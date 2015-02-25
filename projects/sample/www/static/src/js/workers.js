/*
 * JavaScript Web Workers.
 *
 * Copyright (C) 2014 by deipi.com LLC. All rights reserved.
 *
 * Contributing author: German Mendez Bravo (german.mb@deipi.com)
 */

// DISABLED_WORKERS = true;

POLL_SIZE = 6;

workers = {};

if(typeof(window) === 'undefined') {
	var console_log = function(log) {
		return function() {
			try {
				postMessageCompat({
					id: 'console',
					worker: log,
					results: Array.prototype.slice.call(arguments, 0),
					time: 0
				});
			} catch(ex) {
				var results = [];
				for (var i = 0; i < arguments.length; i++) {
					var argument = arguments[i];
					if (typeof argument === 'object') {
						argument = argument.toString();
						if (argument == '[object Object]') {
							try {
								argument = JSON.parse(JSON.stringify(arguments[i]));
							} catch(e) {}
						}
					}
					results.push(argument);
				}
				postMessageCompat({
					id: 'console',
					worker: log,
					results: results,
					time: 0
				});
			}
		};
	};
	console = {};
	console.log = console_log('log');
	console.info = console_log('info');
	console.error = console_log('error');
	console.debug = console_log('debug');
}

stopWorker = function(msg_id) {
	var task = workers.working[msg_id];
	if (task) {
		delete workers.working[msg_id];

		var worker_obj = task.worker_obj;
		if (worker_obj) {
			worker_obj.terminate();

			worker_obj = new workers.Worker(document && document.workers);
			worker_obj.onmessage = workers.onmessage;

			if (workers.taskQueue.length > 0) {
				// don't put back in queue, but execute next task
				task = workers.taskQueue.shift();
				task.worker_obj = worker_obj;
				worker_obj.postMessage(task.msg);
			} else {
				workers.workerQueue.push(worker_obj);
			}
		}
	}
};

dispatchWorker = function(event) {
	var msg = event.data;
	if (msg.id == 'console') {
		console[msg.worker].apply(console, msg.results);
	} else {
		// console.info('Task ' + msg.id + ' finished in ' + msg.time + 'ms.', msg.results);
		var task = workers.working[msg.id];
		if (task) {
			task.callback.apply(this, msg.results);

			delete workers.working[msg.id];

			var worker_obj = task.worker_obj;
			if (workers.taskQueue.length > 0) {
				// don't put back in queue, but execute next task
				task = workers.taskQueue.shift();
				task.worker_obj = worker_obj;
				worker_obj.postMessage(task.msg);
			} else {
				workers.workerQueue.push(worker_obj);
			}
		}
	}
};

callWorker = function(worker, args, callback) {
	workers.id += 1;
	var task = {
		msg: {
			id: worker + '-' + workers.id,
			worker: worker,
			args: args
		},
		callback: callback
	};

	workers.working[task.msg.id] = task;

	if (workers.workerQueue.length > 0) {
		// get the worker from the front of the queue
		var worker_obj = workers.workerQueue.shift();
		task.worker_obj = worker_obj;
		worker_obj.postMessage(task.msg);
	} else {
		// no free workers,
		workers.taskQueue.push(task);
	}
	return task.msg.id;
};

onmessage = function(event) {
	var msg = event.data;
	if (!msg || !msg.worker) {
		return;
	}
	var worker_fn = workers[msg.worker];  // msg.worker must be a registered worker
	if (!worker_fn) {
		console.error("Unregistered JavaScript worker: " + msg.worker);
		return;
	}
	var start = new Date().getTime(),
		results = worker_fn.apply(this, msg.args),
		delta = new Date().getTime() - start;
	postMessageCompat({
		id: msg.id,
		worker: msg.worker,
		results: results,
		time: delta
	});
};

if (typeof(DISABLED_WORKERS) === 'undefined') {
	DISABLED_WORKERS = false;
}

if (typeof(postMessage) !== 'undefined') {
	postMessageCompat = postMessage;
}

if (typeof(Worker) !== 'undefined' && typeof(document) !== 'undefined' && !DISABLED_WORKERS) {
	// console.log('Yes! Web Workers support!');
	if (document.workers) {
		// create 'size' number of worker threads
		workers.Worker = Worker;
		workers.onmessage = dispatchWorker;

		workers.size = POLL_SIZE;
		workers.id = 0;
		workers.working = {};
		workers.taskQueue = [];
		workers.workerQueue = [];
		for (var i = 0 ; i < workers.size ; i++) {
			worker_obj = new workers.Worker(document && document.workers);
			worker_obj.onmessage = workers.onmessage;
			workers.workerQueue.push(worker_obj);
		}
	}
} else if (typeof(window) !== 'undefined') {
	// console.log('No Web Worker...');
	postMessageCompat = function(data) { dispatchWorker({data: data}); };  // IE7 requires to use a different function name

	workers.Worker = function() {
		this.postMessage = function(data) { onmessage({data: data}); };
		this.terminate = function() {};
		this.onmessage = function() {};
	};
	workers.onmessage = onmessage;

	workers.size = 1;
	workers.id = 0;
	workers.working = {};
	workers.taskQueue = [];
	workers.workerQueue = [];
	for (var i = 0 ; i < workers.size ; i++) {
		worker_obj = new workers.Worker(document && document.workers);
		worker_obj.onmessage = workers.onmessage;
		workers.workerQueue.push(worker_obj);
	}
}


/*
// The following is a sample of a worker and how to connect them
workers.primes = function(from, to) {
	// Primes sample worker.
	// Usage: callWorker('primes', [<from>, <to>], function callback(primes) { ... })
	// Example: callWorker('primes', [1, 100], function callback(primes) { alert(primes); })
	var primes = [];
	for (var n = from; n <= to; n += 1) {
		var found = false;
		for (var i = 2; i <= Math.sqrt(n); i += 1) {
			if (n % i === 0) {
				found = true;
				break;
			}
		}
		if (!found) {
			// found a prime!
			primes.push(n);
		}
	}
	return [primes];  // must return a list of arguments to the callback
};
/**/
