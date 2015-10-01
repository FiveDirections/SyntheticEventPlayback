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
import argparse
import sys
from OpenSSL import SSL
from twisted.internet import reactor, ssl
from twisted.internet.protocol import ServerFactory
from twisted.protocols.basic import LineReceiver
from twisted.python import log

debug = False
debug_filename = 'debug_server_data.txt'

class SyntheticListener(LineReceiver):
    def __init__(self):
        self.recv = ''

    def connectionMade(self):
        log.msg('Client connected')

    def connectionLost(self, reason):
        lines = self.recv.split('\r\n')
        headers = lines[:-1]
        body = lines[-1]
        log.msg('headers: ' + str(headers))
        log.msg('body: [' + str(len(body)) + ' bytes]')
        log.msg('Client disconnected')
        if debug:
            f = open(debug_filename, 'a')
            f.write(body + '\n')
            f.close()

    def dataReceived(self, data):
        log.msg('recv: [' + str(len(data)) + ' bytes]')
        self.recv += data
        self.sendLine('OK')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Receive system events from host agents')
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debugging output')
    parser.add_argument(
        '-s', '--ssl',
        nargs=2,
        metavar=('KEY', 'CERT'),
        help='Enable SSL connections with KEY server private key and ' +
            'CERT server certificate.')
    args = parser.parse_args()
    debug = args.debug
    log.startLogging(sys.stdout)
    # Setup and start server
    factory = ServerFactory()
    factory.protocol = SyntheticListener
    reactor.listenTCP(9001, factory)

    if args.ssl:
        secure_factory = ssl.DefaultOpenSSLContextFactory(args.ssl[0], args.ssl[1])
        secure_context = secure_factory.getContext()
        reactor.listenSSL(9443, factory, secure_factory)

    reactor.run()
