"""
Copyright 2015 Five Directions, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from argparse import ArgumentParser
import os
from Queue import Queue
import random
from threading import Lock, Thread, Timer
from time import sleep
import urllib2

from TemplateRandomizer import templateRandomizer

"""
The PlaybackEngine class simulates multiple computers, generating synthetic system events
and sends them to a server via HTTP POST.
"""
class PlaybackEngine:
    def __init__(self, template, machines, iterations, url, output_file, rate, debug):
        self.networker = NetworkingWorker(url, output_file, rate, debug)
        self.template = template
        self.template_worker_list = []
        self.file_lock = Lock()
        self.max_workers = machines
        self.iterations = iterations
        self.debug = debug
        random.seed()

        # Spawn machines # of threads
        while self.active_workers() < self.max_workers:
            self.spawn_worker()

    """
    Stop all running worker threads and the networker thread.
    If the engine has been running indefinitely, allow for the networker to finish
    sending events off the queue.
    """
    def stop(self):
        print "Killing all workers."
        for t in self.template_worker_list:
            if t.is_alive():
                t.close()
        if self.iterations != 0:
            if self.networker.is_alive():
                self.networker.close()
        # Special case if we're looping indefinitely
        else:
            try:
                print 'Requesting for the networker to finish, press <Ctrl-C> again to force termination.'
                self.networker.finish_then_close()
            except KeyboardInterrupt:
                if self.networker.is_alive():
                    self.networker.close()

    """
    Starts the initial worker threads and then spawns more as needed.
    User may quit at any time by pressing Ctrl-C.
    """
    def start(self):
        print "Starting playback engine."
        try:
            self.networker.start()
            for t in self.template_worker_list:
                t.start()

            # Wait for all the workers to finish
            while self.active_workers():
                sleep(0.5)
            # Wait for the networking thread to finish sends
            self.networker.finish_then_close()

        except KeyboardInterrupt:
            # Listen for a keyboard interrupt and stop when given
            self.stop()

    """
    Creates a new worker thread and adds it to the worker list.
    Increments the current iteration of the template that we're on
    """
    def spawn_worker(self):
        new_worker = TemplateWorker(len(self.template_worker_list),
            self.template, self.file_lock, self.iterations, self.networker.add_event_to_batch,
            self.debug, self.worker_callback)
        self.template_worker_list.append(new_worker)
        return new_worker

    """
    Returns the number of workers that have been created but not finished
    """
    def active_workers(self):
        return len(self.template_worker_list)

    """
    Callback for workers when finished. Removes self from the list of active workers
    """
    def worker_callback(self, worker):
        self.template_worker_list.remove(worker)

"""
The TemplateWorker class reads in synthetic events from a file and passes the events
to the NetworkingWorker. Spawns as a separate thread.
"""
class TemplateWorker(Thread):
    def __init__(self, id, template_dir, file_lock, iterations, output_call, debug, callback=None):
        Thread.__init__(self)
        self.id = str(id)
        self.stop = False
        self.file_lock = file_lock
        self.template_set = []
        if os.path.isdir(template_dir):
            ls = os.listdir(template_dir)
            for filename in ls:
                # ignore hidden files
                if filename[0] != '.':
                    self.template_set.append(os.path.normpath(template_dir + '/' + filename))
        else:
            self.template_set.append(template_dir)
        self.max_iterations = iterations
        self.current_iteration = 0
        self.output_call = output_call
        self.debug = debug
        if debug:
            self.debug_file = open('debug_worker' + self.id + '-events.txt', 'w')
        self.value_filename = 'host' + self.id + '_values.txt'
        self.callback = callback

    def run(self):
        print "Starting worker #{0}.".format(self.id)
        self.template = self.select_template()
        self.randomizer = templateRandomizer(self.open_template())
        if not self.randomizer.generate_test():
            print 'Invalid template file: {0}\nStopping worker #{1}'.format(self.template, self.id)
            self.stop = True
        while self.need_more_templates() and not self.stop:
            print "Worker #{0} synthesizing events from [{1}]".format(self.id, self.template)
            if self.debug:
                self.template_debug_file = open(
                    'debug_worker' + self.id + '-template' + str(self.current_iteration) + '.txt', 'w')
            line = self.randomizer.next_event()
            while line != None and not self.stop:
                # remove the list brackets and trailing newline character
                data = line[1:-2]
                if self.debug:
                    self.debug_file.write(str(data) + '\n')
                    self.template_debug_file.write(str(data) + '\n')
                self.output_call(data)
                line = self.randomizer.next_event()

            value_file = open(self.value_filename, 'w')
            self.randomizer.write_test_values(value_file)
            value_file.close()

            if self.debug:
                self.template_debug_file.close()

            # Select and start next template
            self.template = self.select_template()
            self.randomizer = templateRandomizer(self.open_template())
            # This time reuse host and user info from previous templates
            value_file = open(self.value_filename, 'r')
            if not self.randomizer.generate_test_reuse_host(value_file):
                print 'Invalid template file: {0}\nStopping worker #{1}'.format(self.template, self.id)
                self.stop = True
            value_file.close()
            self.current_iteration += 1

        if self.debug:
            self.debug_file.close()
        if self.callback:
            self.callback(self)
        print "Worker #{0} has stopped.".format(self.id)

    """
    Send a signal for the worker to stop.
    """
    def close(self):
        self.stop = True

    """
    If template_set is a directory, select a template to use at random;
    otherwise use the specified file as the template.
    """
    def select_template(self):
        select = random.randint(0, len(self.template_set) -1)
        return self.template_set[select]

    """
    Acquire a lock given by the engine to prevent simultaneous file I/O.
    Returns a handle to the template.
    """
    def open_template(self):
        self.file_lock.acquire()
        file = open(self.template, 'r')
        self.file_lock.release()
        return file

    """
    Check if we're done with opening templates.
    """
    def need_more_templates(self):
        return (self.current_iteration < self.max_iterations) or self.max_iterations == 0

"""
The NetworkingWorker class batches events and sends them to the specified server via
HTTP POST.
"""
class NetworkingWorker(Thread):
    def __init__(self, url, output_file, rate_limit=0, debug=False):
        Thread.__init__(self)

        self.stop = False
        self.url = url
        self.send_queue = Queue(300000) # maxsize = 300k events; total mem usage approx 700MB
        self.batch_lock = Lock()

        self.batch_limit = 1000 # 1k strikes a balance between throughput and creating connections
        self.wait_limit = 1 # second
        self.retry_send = False

        self.rate_limited = False
        if rate_limit:
            self.batch_limit = rate_limit
            self.rate_limited = True
        self.send_timer = Timer(self.wait_limit, self.send_batch)
        self.batch = []
        self.debug = debug
        if output_file:
            self.output_file = open(output_file, 'w')
        elif debug:
            self.output_file = open('debug_network_batch.txt', 'w')
        else:
            self.output_file = None

    def run(self):
        print "Starting networking worker."
        # Start the timers
        self.send_timer.start()

        while not self.stop:
            while len(self.batch) < self.batch_limit:
                self.batch_lock.acquire()
                if not self.send_queue.empty():
                    self.batch.append(self.send_queue.get())
                    self.batch_lock.release()
                else:
                    self.batch_lock.release()
                    break

                # If the batch has reached our limit and we are not rate limiting,
                # send it away
                # Otherwise, the timer will take care of sending
                if len(self.batch) >= self.batch_limit and not self.rate_limited and not self.retry_send:
                    self.send_batch()
            sleep(0.05)
        # Empty out the queue so that any blocking workers may finish
        while not self.send_queue.empty():
            self.send_queue.get(True, 1)
        self.batch = []
        if self.output_file:
            self.output_file.close()

        print 'Networker has stopped.'

    def add_event_to_batch(self, event):
        # Put an event into the queue -- will block if the queue is full
        self.send_queue.put(event)

    """
    Send the batch away when it is either full or enough time has passed
    """
    def send_batch(self):
        # Cancel the timer
        self.send_timer.cancel()

        self.batch_lock.acquire()
        self.retry_send = False
        if len(self.batch) > 0 and not self.stop:
            # format the batch to match JSON specs
            post = '[' + ','.join(self.batch) + ']'
            request = urllib2.Request(self.url, post)
            # Send the events and receive response
            # Fire and forget
            try:
                response = urllib2.urlopen(request, timeout=0.05)
            except urllib2.URLError as e:
                print 'Could not connect to {0}\nRetrying in {1} seconds...'.format(self.url, self.wait_limit)
                self.retry_send = True
            except:
                # Some targets might not respond at all
                pass
            if self.output_file:
                self.output_file.write(post + '\n')

            # If the send was successful, clear the batch
            if not self.retry_send:
                self.batch = []
        self.batch_lock.release()
        # Restart the timer
        if not self.stop:
            self.send_timer = Timer(self.wait_limit, self.send_batch)
            self.send_timer.start()

    """
    Ask the worker nicely to off itself.
    """
    def close(self):
        # Cancel the timer
        self.send_timer.cancel()
        self.stop = True

    """
    Wait for everything in the queue to be sent before closing the worker.
    """
    def finish_then_close(self):
        while not (self.send_queue.empty() and len(self.batch) == 0):
            sleep(1)
        self.close()

if __name__ == "__main__":
    parser = ArgumentParser(
        description='Generate and send synthetic events to system event managers.')
    parser.add_argument(
        'templates',
        help='The event template or directory of templates to generate synthetic events from.'
    )
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debugging output.')
    parser.add_argument(
        '-i', '--iterations',
        type=int,
        metavar='NUM',
        default=1,
        help='Run through NUM templates. Specifying 0 will run continuously.')
    parser.add_argument(
        '-m', '--machines',
        type=int,
        metavar='NUM',
        default=1,
        help='The number of machine hosts to simulate -- a thread will be spawned for each machine.')
    parser.add_argument(
        '-n', '--rate',
        type=int,
        metavar='NUM',
        default=0,
        help='Limit the rate of events sent over the network to NUM events per second.')
    parser.add_argument(
        '-o', '--output',
        metavar='FILE',
        help='Write the generated events out to FILE.')
    parser.add_argument(
        '-u', '--url',
        metavar='URL',
        help='The URL to send events to.',
        required=True)
    parser.add_argument(
        '-v', '--version',
        action='version', version='%(prog)s v1.0')
    args = parser.parse_args()
    if args.debug:
        print 'Debug mode enabled.'
    engine = PlaybackEngine(args.templates, args.machines, args.iterations, args.url,
        args.output, args.rate, args.debug)
    engine.start()
