from flask import Flask, render_template, request, Blueprint
from datetime import datetime, timedelta
import random

learning_bp = Blueprint('learning', __name__, template_folder='templates')

def calculate_fitness(tasks, schedule):
    total_duration = sum(task["duration"] for task in tasks)
    schedule_duration = sum(
        (datetime.strptime(task["end_time"], "%H:%M") - datetime.strptime(task["start_time"], "%H:%M")).seconds / 60
        for task in schedule
    )
    fitness = total_duration - abs(total_duration - schedule_duration)
    return fitness

from queue import PriorityQueue

def generate_schedule(tasks, start_time, end_time, break_times):
    num_schedules = 1
    best_schedule = []
    best_fitness = float("-inf")

    for _ in range(num_schedules):
        current_time = start_time
        schedule = []

        for break_start, break_end in break_times:
            schedule.append(
                {"task_name": "Break", "start_time": break_start.strftime("%H:%M"), "end_time": break_end.strftime("%H:%M")}
            )

        tasks_sorted = sorted(tasks, key=lambda x: x["duration"])
        task_queue = PriorityQueue()

        for task in tasks_sorted:
            task_queue.put((task["duration"], task))

        while not task_queue.empty():
            duration, task = task_queue.get()
            task_start_time = None
            task_end_time = None

            for break_start, break_end in break_times:
                if current_time < break_start:
                    task_start_time = current_time
                    task_end_time = min(current_time + timedelta(minutes=duration), break_start)
                else:
                    task_start_time = max(current_time, break_end)
                    task_end_time = task_start_time + timedelta(minutes=duration)

            if task_start_time is None:
                task_start_time = current_time
                task_end_time = current_time + timedelta(minutes=duration)

            if not (start_time <= task_start_time < end_time and start_time < task_end_time <= end_time):
                raise ValueError("Schedule not feasible for given input")
            print(task_start_time,task_end_time)
            # Check if the task duration is less than or equal to the available time slot
            if (task_end_time - task_start_time).total_seconds() >= duration * 60:
                schedule.append(
                    {"task_name": task["task_name"], "start_time": task_start_time.strftime("%H:%M"),
                     "end_time": task_end_time.strftime("%H:%M")}
                )
                current_time = task_end_time
            else:
                schedule.append(
                    {"task_name": task["task_name"], "start_time": task_start_time.strftime("%H:%M"),
                     "end_time": task_end_time.strftime("%H:%M")}
                )
                current_time = task_end_time
                # Put the task back in the queue with remaining duration
                remaining_duration = duration - (task_end_time - task_start_time).total_seconds() / 60
                task_queue.put((remaining_duration, task))
    sorted_schedule=sorted(schedule, key=lambda x: x["start_time"])
    return sorted_schedule



def initialize_population(tasks, start_time, end_time, break_times, population_size):
    population = []
    for _ in range(population_size):
        shuffled_tasks = random.sample(tasks, len(tasks))
        schedule = generate_schedule(shuffled_tasks, start_time, end_time, break_times)
        population.append(schedule)
    return population

def crossover(parent1, parent2):
    if len(parent1) == len(parent2):
        return parent1  # No crossover needed when lengths are the same

    crossover_point = random.randint(1, min(len(parent1), len(parent2)) - 1)
    child = parent1[:crossover_point] + parent2[crossover_point:]
    return child

def mutate(schedule, mutation_rate):
    for task in schedule:
        if random.random() < mutation_rate:
            # Implement mutation logic if needed
            # For simplicity, this example does not include specific mutation logic
            pass
    return schedule

def genetic_algorithm(tasks, start_time, end_time, break_times, population_size=10, generations=100, mutation_rate=0.1):
    try:
        population = initialize_population(tasks, start_time, end_time, break_times, population_size)
        print(population)
        best_schedule = None
        best_fitness = float("-inf")

        for _ in range(generations):
            fitness_scores = [calculate_fitness(tasks, schedule) for schedule in population]

            selected_indices = random.choices(range(population_size), weights=fitness_scores, k=population_size)
            selected_population = [population[i] for i in selected_indices]

            next_generation = []
            for _ in range(population_size // 2):
                parent1 = random.choice(selected_population)
                parent2 = random.choice(selected_population)
                child1 = crossover(parent1, parent2)
                child2 = crossover(parent2, parent1)
                child1 = mutate(child1, mutation_rate)
                child2 = mutate(child2, mutation_rate)
                next_generation.extend([child1, child2])

            population = next_generation

            current_best_schedule = max(population, key=lambda schedule: calculate_fitness(tasks, schedule))
            current_best_fitness = calculate_fitness(tasks, current_best_schedule)

            if current_best_fitness > best_fitness:
                best_schedule = current_best_schedule
                best_fitness = current_best_fitness

        return best_schedule
    except Exception as e:
        return None

@learning_bp.route('/', methods=['GET', 'POST'])
def learning_index():
    if request.method == 'POST':
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        break_start_times = request.form.getlist('break_start_times[]')
        break_end_times = request.form.getlist('break_end_times[]')

        start_time = datetime.strptime(start_time, "%H:%M")
        end_time = datetime.strptime(end_time, "%H:%M")

        if break_start_times and break_end_times:
            # Breaks are provided
            break_times = [(datetime.strptime(start, "%H:%M"), datetime.strptime(end, "%H:%M")) for start, end in
                           zip(break_start_times, break_end_times)]
        else:
            # No breaks provided
            break_times = []
        
        task_names = request.form.getlist('task_names[]')
        task_durations = request.form.getlist('task_durations[]')
        tasks = [{"task_name": name, "duration": int(duration)} for name, duration in zip(task_names, task_durations)]
        

        try:
            for break_start, break_end in break_times:
                if not (start_time <= break_start < end_time and start_time < break_end <= end_time):
                    raise ValueError("Break times must be within the specified start and end times.")

            best_schedule = generate_schedule(tasks, start_time, end_time, break_times)

            if best_schedule is not None:
                return render_template('schedule.html', best_schedule=best_schedule)
            else:
                error_message = "Unable to generate a valid schedule. Please adjust your input parameters."
                return f'<script>alert("{error_message}"); window.history.back();</script>'
        except ValueError as e:
            error_message = str(e)
            return render_template('scheduler_index.html', error_message=error_message)

    return render_template('scheduler_index.html')

