from threading import Thread

import job_manager
import experiment_receiver
import monitoring

from experiment import Experiment 
from parameters import http_server_port, metrics_server_port

import logging

""" Configure logging """
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
conlog = logging.StreamHandler()
conlog.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
conlog.setFormatter(formatter)
logger.addHandler(conlog)
logger.debug("Logging configured.")

experiments = {}

if __name__ == '__main__':
	# Starting the job manager
	job_manager_thread = Thread(target = job_manager.start_job_manager, args = ())
	job_manager_thread.start()

	# Starting the experiment receiver
	experiment_receiver_thread = Thread(target = experiment_receiver.start, args = (experiments, http_server_port))
	experiment_receiver_thread.start()

	metrics_server_thread = Thread(target = monitoring.start, args = (metrics_server_port,))
	metrics_server_thread.start()