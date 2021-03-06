""" Storing values in the monitoring system with prometheus """
import time
import sys
import copy
import logging

from prometheus_client import start_http_server, Gauge, Counter

logger = logging.getLogger(__name__)

# Number of jobs added
JQUEUER_JOB_ADDED = "jqueuer_job_added"
JQUEUER_TASK_ADDED = "jqueuer_task_added"
JQUEUER_EXPERIMENT_ADDING_TIMESTAMP = "jqueuer_experiment_adding_timestamp"
JQUEUER_EXPERIMENT_DEADLINE = "jqueuer_experiment_deadline"
JQUEUER_EXPERIMENT_TASK_DURATION = "jqueuer_single_task_duration"
    
job_added = Gauge(JQUEUER_JOB_ADDED, "Time when job added", ["experiment_id", "service_name", "job_id"])
task_added = Gauge(JQUEUER_TASK_ADDED, "Time when task added", ["experiment_id", "service_name", "job_id", "task_id"])
exp_added = Gauge(JQUEUER_EXPERIMENT_ADDING_TIMESTAMP, "Time when exp added", ["experiment_id", "service_name"])
exp_deadl = Gauge(JQUEUER_EXPERIMENT_DEADLINE, "Experiment deadline", ["experiment_id", "service_name"])
task_dur = Gauge(JQUEUER_EXPERIMENT_TASK_DURATION, "Experiment task duration", ["experiment_id", "service_name"])

# Keep track of experiment statistics

# Dictionary list of running jobs - key = worker_id, Value = {job_id,start_time}
running_jobs = {}

# List of all active workers (containers)
list_active_workers = []  

# List of nodes those are selected for deletion
list_nodes_to_scale_down = []

# current experiment id
current_experiment_id = ""

# ---------------------------------------

def start(metric_server_port):
    start_http_server(metric_server_port)

def add_job(experiment_id, service_name, job_id):
    job_added.labels(experiment_id, service_name, job_id).set(time.time())

def add_task(experiment_id, service_name, job_id, task_id):
    task_added.labels(experiment_id, service_name, job_id, task_id).set(time.time())

def experiment_adding_timestamp(experiment_id, service_name, experiment_adding_timestamp):
    exp_added.labels(experiment_id, service_name).set(experiment_adding_timestamp)

def experiment_deadline(experiment_id, service_name, experiment_deadline):
    exp_deadl.labels(experiment_id, service_name).set(experiment_deadline)

def experiment_task_duration(experiment_id, service_name, single_task_duration):
    task_dur.labels(experiment_id, service_name).set(single_task_duration)

def clear_lists():
    global running_jobs, list_active_workers, list_nodes_to_scale_down, current_experiment_id
    list_active_workers.clear()
    list_nodes_to_scale_down.clear()
    for worker_id in running_jobs:
        entry = running_jobs[worker_id]
        job_id = entry["job_id"]
        job_running.labels(getNodeID(worker_id), current_experiment_id,getServiceName(worker_id),getContainerID(worker_id),job_id).set(0)
    running_jobs.clear()

# J-queuer Agent metrics
node_counter = Gauge("jqueuer_worker_count", "JQueuer Worker", ["node_id","service_name","qworker_id"])
job_running_timestamp = Gauge("jqueuer_job_running_timestamp","jqueuer_job_running_timestamp",["node_id","experiment_id","service_name","job_id"])
job_running = Gauge("jqueuer_job_running","jqueuer_job_running",["node_id","experiment_id","service_name","qworker_id","job_id"])
job_started = Gauge("jqueuer_job_started","jqueuer_job_started",["node_id","experiment_id","service_name","qworker_id","job_id"])
job_accomplished_timestamp = Gauge("jqueuer_job_accomplished_timestamp","jqueuer_job_accomplished_timestamp",["node_id","experiment_id","service_name","job_id"])
job_accomplished_duration = Gauge("jqueuer_job_accomplished_duration","jqueuer_job_accomplished_duration",["node_id","experiment_id","service_name","job_id"])
job_accomplished = Gauge("jqueuer_job_accomplished","jqueuer_job_accomplished",["node_id","experiment_id","service_name","qworker_id","job_id"])
job_failed_timestamp = Gauge("jqueuer_job_failed_timestamp","jqueuer_job_failed_timestamp",["node_id","experiment_id","service_name","job_id"])
job_failed_duration = Gauge("jqueuer_job_failed_duration","jqueuer_job_failed_duration",["node_id","experiment_id","service_name","job_id"])
job_failed_ga = Gauge("jqueuer_job_failed","jqueuer_job_failed",["node_id","experiment_id","service_name","qworker_id","job_id"])
task_running_timestamp = Gauge("jqueuer_task_running_timestamp","jqueuer_task_running_timestamp",["node_id","experiment_id","service_name","job_id","task_id"]) 
task_running = Gauge("jqueuer_task_running","jqueuer_task_running",["node_id","experiment_id","service_name","qworker_id","job_id","task_id"])
task_started = Gauge("jqueuer_task_started","jqueuer_task_started",["node_id","experiment_id","service_name","qworker_id","job_id","task_id"])
task_accomplished_timestamp = Gauge("jqueuer_task_accomplished_timestamp","jqueuer_task_accomplished_timestamp",["node_id","experiment_id","service_name","job_id","task_id"])
task_accomplished_duration = Gauge("jqueuer_task_accomplished_duration","jqueuer_task_accomplished_duration",["node_id","experiment_id","service_name","job_id","task_id"])
task_accomplished = Gauge("jqueuer_task_accomplished","jqueuer_task_accomplished",["node_id","experiment_id","service_name","qworker_id","job_id","task_id"])
task_failed_timestamp = Gauge("jqueuer_task_failed_timestamp","jqueuer_task_failed_timestamp",["node_id","experiment_id","service_name","job_id","task_id"])
task_failed_duration = Gauge("jqueuer_task_failed_duration","jqueuer_task_failed_duration",["node_id","experiment_id","service_name","qworker_id","job_id","task_id"])
task_failed_ga = Gauge("jqueuer_task_failed","jqueuer_task_failed",["node_id","experiment_id","service_name","qworker_id","job_id","task_id"])
idle_nodes = Gauge("jqueuer_idle_nodes","jqueuer_idle_nodes",["node_id","experiment_id"])
exp_deleted = Gauge("jqueuer_is_exp_deleted","jqueuer_is_exp_deleted",["experiment_id"])

def start_experiment(experiment_id):
    global current_experiment_id
    current_experiment_id = experiment_id

def delete_experiment():
    global current_experiment_id
    exp_deleted.labels(current_experiment_id).set(1)
    current_experiment_id = ""

def add_worker(worker_id):
    global running_jobs, list_active_workers
    worker_id = worker_id.split("@")[1]
    node_counter.labels(getNodeID(worker_id),getServiceName(worker_id),getContainerID(worker_id)).set(1)
    if worker_id not in list_active_workers:
        list_active_workers.append(worker_id)
                
def terminate_worker(worker_id):
    global running_jobs, list_active_workers, list_nodes_to_scale_down, current_experiment_id
    worker_id = worker_id.split("@")[1]
    node_id = getNodeID(worker_id)
    node_counter.labels(node_id,getServiceName(worker_id),getContainerID(worker_id)).set(0)
    # Handle if there is any running job
    if worker_id in running_jobs:
        entry = running_jobs[worker_id]
        job_id = entry["job_id"]
        job_running.labels(node_id, current_experiment_id,getServiceName(worker_id),getContainerID(worker_id),job_id).set(0)
        del running_jobs[worker_id]
    # Handle the list_of_active_worker
    if worker_id in list_active_workers:
        list_active_workers.remove(worker_id)
    # Handle, if node of the work is previously selected for deletion
    if len(list_nodes_to_scale_down) > 0 and node_id in list_nodes_to_scale_down and check_node_running_jobs(node_id) == False:
        list_nodes_to_scale_down.remove(node_id)

def run_job(qworker_id, experiment_id, job_id):
    start_time = time.time()
    job_running_timestamp.labels(getNodeID(qworker_id), experiment_id,getServiceName(qworker_id),job_id).set(start_time)
    job_running.labels(getNodeID(qworker_id), experiment_id,getServiceName(qworker_id),getContainerID(qworker_id),job_id).set(1)
    running_jobs[qworker_id]={'job_id':job_id, 'start_time':start_time}
    
def terminate_job(qworker_id, experiment_id, job_id, start_time):
    elapsed_time = time.time() - start_time
    node_id = getNodeID(qworker_id)
    service_name = getServiceName(qworker_id)
    container_id = getContainerID(qworker_id)
    job_accomplished_timestamp.labels(node_id,experiment_id,service_name,job_id).set(time.time())
    job_accomplished_duration.labels(node_id,experiment_id,service_name,job_id).set(elapsed_time)
    job_accomplished.labels(node_id,experiment_id,service_name,container_id,job_id).set(1)
    return terminate_running_job(qworker_id, experiment_id, job_id)

def terminate_running_job(qworker_id, experiment_id, job_id):
    global running_jobs, list_active_workers, list_nodes_to_scale_down
    job_running.labels(getNodeID(qworker_id), experiment_id,getServiceName(qworker_id),getContainerID(qworker_id),job_id).set(0)
    if qworker_id in running_jobs:
        del running_jobs[qworker_id]

    # check if node of the worker is idle and can be publish for release
    if len(list_nodes_to_scale_down) > 0:
        node_id = getNodeID(qworker_id)
        if node_id in list_nodes_to_scale_down:
            node_counter.labels(getNodeID(qworker_id),getServiceName(qworker_id),getContainerID(qworker_id)).set(0)
            list_active_workers.remove(qworker_id)
            if check_node_running_jobs(node_id) == False:
                idle_nodes.labels(node_id, experiment_id).set(1)
                list_nodes_to_scale_down.remove(node_id)
            return "stop_worker"
    return ""

def check_immediate_node_release():
    global list_active_workers, list_nodes_to_scale_down
    # check if node of the worker is idle and can be publish for release
    for node_id in list_nodes_to_scale_down:
        if check_node_running_jobs(node_id) == False:
            # Terminate workers
            exp_id = ""
            for worker_id in get_node_workers(node_id):
                node_counter.labels(node_id,getServiceName(worker_id),getContainerID(worker_id)).set(0)
                list_active_workers.remove(worker_id)
            # expose metric
            idle_nodes.labels(node_id, exp_id).set(1)
            list_nodes_to_scale_down.remove(node_id)
        
def get_node_workers(node_id):
    global list_active_workers
    list_node_workers = []
    for w_id in list_active_workers:
        if getNodeID(w_id) == node_id:
            list_node_workers.append(w_id)
    return list_node_workers

def check_node_running_jobs(node_id):
    global running_jobs
    for w_id in running_jobs:
        if getNodeID(w_id) == node_id:
            return True
    return False             
        
def job_failed(qworker_id, experiment_id, job_id, fail_time):
    elapsed_time = time.time() - fail_time
    node_id = getNodeID(qworker_id)
    service_name = getServiceName(qworker_id)
    container_id = getContainerID(qworker_id)
    job_failed_timestamp.labels(node_id,experiment_id,service_name,job_id).set(time.time())
    job_failed_duration.labels(node_id,experiment_id,service_name,job_id).set(elapsed_time)
    job_failed_ga.labels(node_id,experiment_id,service_name,container_id,job_id).set(1)
    return terminate_running_job(qworker_id,experiment_id,job_id)

def run_task(qworker_id, experiment_id, job_id, task_id):
    node_id = getNodeID(qworker_id)
    service_name = getServiceName(qworker_id)
    container_id = getContainerID(qworker_id)
    task_running_timestamp.labels(node_id,experiment_id,service_name,job_id,task_id).set(time.time())
    task_running.labels(node_id,experiment_id,service_name,container_id,job_id,task_id).set(1)

def terminate_task(qworker_id, experiment_id, job_id, task_id, start_time):
    elapsed_time = time.time() - start_time
    node_id = getNodeID(qworker_id)
    service_name = getServiceName(qworker_id)
    container_id = getContainerID(qworker_id)
    task_accomplished_timestamp.labels(node_id,experiment_id,service_name,job_id,task_id).set(time.time())
    task_accomplished_duration.labels(node_id,experiment_id,service_name,job_id,task_id).set(elapsed_time)
    task_accomplished.labels(node_id,experiment_id,service_name,container_id,job_id,task_id).set(1)
    task_running.labels(node_id,experiment_id,service_name,container_id,job_id,task_id).set(0)

def task_failed(qworker_id, experiment_id, job_id, task_id, fail_time):
    elapsed_time = time.time() - fail_time
    node_id = getNodeID(qworker_id)
    service_name = getServiceName(qworker_id)
    container_id = getContainerID(qworker_id)
    task_failed_timestamp.labels(node_id,experiment_id,service_name,job_id,task_id).set(time.time())
    task_failed_duration.labels(node_id,experiment_id,service_name,container_id,job_id,task_id).set(elapsed_time)
    task_failed_ga.labels(node_id,experiment_id,service_name,container_id,job_id,task_id).set(1)
    task_running.labels(node_id,experiment_id,service_name,container_id,job_id,task_id).set(0)

# Get Worker ID
def getNodeID(worker_id):
    return worker_id.split("##")[0]


# Get Service Name
def getServiceName(worker_id):
    return worker_id.split("##")[1]


# Get Container ID
def getContainerID(worker_id):
    return worker_id.split("##")[2]