"""
Copyright 2015 Palo Alto Research Center, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Coded by rui@parc.com
"""
import json
from pprint import pprint
import sys
import optparse

class FD2PN(object):
    """FiveDirections Simulator Data to TC's ADAPT PROV-N"""

    setAgents = {}
    setEntities = {}
    tmpPID = {}

    def pretty_print_agent(self):
        for key in self.setAgents:
            value = self.setAgents[key]
            print 'agent(ex:ag{}, [prov:type="adapt:unitOfExecution"' . format(value['index'])
            print '\tadapt:machineID = "{}",' . format(value['adapt:machineID'])
            if "foaf:accountName" in value:
                print '\tfoaf:name = "{}",' . format(value['foaf:name'])
                print '\tfoaf:accountName = "{}"])\n' . format(value['foaf:accountName'])
            else:
                print '\tfoaf:name = "{}"])\n' . format(value['foaf:name'])

    def pretty_print_entities(self):
        for key in self.setEntities:
            value = self.setEntities[key]
            print 'entity(ex:ent{}, [\
                  \n\tprov:type=adapt:artifact,\
                  \n\tadapt:artifactType="file",\
                  \n\tadapt:filePath="{}"])\n' . format(value['index'], value['dir'] + value['file'])

    def getAgents(self,value):
        agent = value['host'] + '_' + str(value['pid'])
        if(agent not in self.setAgents):
            agProperties = {}
            agProperties['adapt:machineID'] = value['host']
            agProperties['foaf:name'] = value['process']
            if 'user' in value:
                agProperties['foaf:accountName'] = value['user']
            agProperties['index'] = value['index']
            self.setAgents[agent] = agProperties

    def getEntities(self,value):
        entity = value['dir'] + "\\" + value['file']
        if(entity not in self.setEntities):
            eProperties = {}
            eProperties['dir'] = value['dir']
            eProperties['file'] = value['file']
            eProperties['index'] = value['index']
            self.setEntities[entity] = eProperties

    def encodeProcess(self,value):
        print 'activity(ex:act{}, -, -, [\n\tprov:type=\'adapt:unitOfExecution\',\
        \n\tadapt:machineID="{}",\
        \n\tfoaf:accountName="{}",\
        \n\tadapt:pwd="{}",\
        \n\tprov:startedAtTime="{}",\
        \n\tadapt:pid="{}",\
        \n\tadapt:ppid="{}",\
        \n\tadapt:privs="{}",\
        \n\tadapt:cmdLine="{}",\
        \n\tadapt:cmdString="{}"])\n' . format(value['index'], value['host'], value['user'], value['dir'],
                                               value['time'], value['pid'], value['ppid'],
                                               value['elevation'], value['cmd'], value['cmd'])

        kk = str(value['ppid']) + "_" + value['file']
        activity = self.tmpPID[kk] if kk in self.tmpPID else 0
        print 'wasStartedBy(ex:act{}, ex:act{}, {}, [\
        \n\tprov:startedAtTime="{}"])\n' . format(value['index'], activity, value['time'], value['time'])


    def encodeFile(self, value):
        print 'activity(ex:act{}, -, -, [\n\tprov:type=\'adapt:unitOfExecution\',\
        \n\tadapt:machineID="{}",\
        \n\tprov:startedAtTime="{}",\
        \n\tadapt:pid="{}",\
        \n\tadapt:cmdLine="{}",\
        \n\tadapt:cmdString="{}"])\n' . format(value['index'], value['host'],
                                               value['time'], value['pid'],
                                               value['process'], value['process'])

        print 'wasAssociatedWith(ex:as{}, ex:act{}, ex:ag{}, -, -)\n' . format(value['index'], value['index'], value['index'])

        print 'used(ex:us{}, ex:act{}, ex:ent{}, "{}", [adapt:useOp="{}"])\n' . format(value['index'],
                                                            value['index'], value['index'],
                                                            value['time'], value['action'])

        kk = str(value['pid']) + "_" + value['file']
        self.tmpPID[kk] = "ex:act" + str(value['index'])

    def encodeNetwork(self, value):
        print 'entity(ex:socket{}, [prov:type=adapt:artifact])\n' . format(value['index'])

        print 'dc:description(ex:socket{}, [\
            \n\tprov:type=tc:metadata,\
            \n\ttc:dstPortID="{}",\
            \n\ttc:srcPort="{}",\
            \n\ttc:srcIP="{}",\
            \n\ttc:dstIP="{}",\
            \n\ttc:host="{}",\
            \n\ttc:protocol="{}"])\n' . format(value['index'],
                                         value['dport'],
                                         value['sport'],
                                         value['saddr'],
                                         value['daddr'],
                                         value ['host'],
                                         value['protocol'])

        print 'wasAssociatedWith(ex:as{}, ex:a{}, ex:ag{}, -, [])\n' . format(value['index'], value['index'], value['index'])
        print 'wasGeneratedBy(ex:e{}, ex:a{}, -, [tc:genOp="{}", prov:atTime="{}"])\n' . format(value['index'], value['index'],
                                                                                    value['action'], value['time'])

    def encodeRegistry(self, value):
        print 'entity(ex:reg{}, [\
        \n\tprov:type=adapt:artifact,\
        \n\tadapt:artifactType="registryEntry",\
        \n\tadapt:registryKey="{}"])\n' . format(value['index'],value['key'])

        print 'activity(ex:act{}, -, -, [\n\tprov:type=\'adapt:unitOfExecution\',\
        \n\tadapt:machineID="{}",\
        \n\tprov:startedAtTime="{}",\
        \n\tadapt:pid="{}",\
        \n\tadapt:cmdLine="{}",\
        \n\tadapt:cmdString="{}"])\n' . format(value['index'], value['host'],
                                               value['time'], value['pid'],
                                               value['process'], value['process'])

        print 'wasGeneratedBy(ex:wgb{}, ex:reg1, ex:act299, -, [\
        \n\tadapt:genOp="{}",\
        \n\tadapt:registryValue="{}",\
        \n\tadapt:registryType="{}"])\n' . format(value['index'], value['action'], value['newval'], value['newtype'])

    def json2Prov(self, json):
        for i in xrange(len(decoded)):
            for key, value in decoded[i].items() :
                if(key=='file' or key=='network' or key=='registry'):
                    self.getAgents(value)
                if(key=='file'):
                    self.getEntities(value)

        self.pretty_print_agent()
        self.pretty_print_entities()

        for i in xrange(len(decoded)):
            for key, value in decoded[i].items():
                if(key=='file'):
                    self.encodeFile(value)
                elif(key=='process'):
                    self.encodeProcess(value)
                elif(key=='registry'):
                    self.encodeRegistry(value)
                elif(key=='network'):
                    self.encodeNetwork(value)
                else:
                    print >>sys.stderr, "fatal error: " + key

#with open('youtube.txt') as data_file:
#    data = json.load(data_file)
if __name__ == '__main__':
    usage = "usage: %prog fileName"
    optp = optparse.OptionParser(usage = usage, version = "%prog 1.0")

    opts, args = optp.parse_args()
    optp.parse_args()

    with open(args[0]) as f:
        content = f.readlines()

    fs2pn = FD2PN()
    for i in xrange(1,len(content)):
        if(i % 9 == 0):
            decoded = json.loads(content[i-1])
            #print json.dumps(decoded, sort_keys=True, indent=4)
            fs2pn.json2Prov(decoded)
