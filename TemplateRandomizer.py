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
import fileinput
import sys
import string
import random
import re
import time
import argparse
import os.path

'''This program inputs a template and outputs 2 files: the first is the template with
randomized data inserted, the second is a text file with a key to the data so
the template can be re-replicated'''

#Class with methods to write strings for key file
class writeKey:

    def turnToString(self, variableName, generatedData):
        return ("\n\nVariable name: " + variableName + ", Generated value: " + generatedData)

    #Method prints out dictionary
    def dictToString(self, dictionary, variableName):
        line = "\n\n" + variableName[1:len(variableName)] + " list:" + "\n"#removes $ from variable name
        for key in dictionary:
            line = line + variableName + str(key) + ": " + str(dictionary[key]) + "\n\n"
        return line
#End class

#Class with methods to find variables from key file
class findVariables:

    #Method to return variable
    def returnVariable(self, line, before_substring, after_substring):
        start_of_variable = len(before_substring)
        end_of_variable = line.find(after_substring)
        variable = line[start_of_variable:end_of_variable]
        return (variable)

    def returnVariableWithNoEnd(self, line, before_substring):
        start_of_variable = line.find(before_substring) + len(before_substring)
        variable = line[start_of_variable:]
        return variable
#End class

class replaceVariables:
    def removeAndReplaceVariable(self, line, variable_to_remove, variable_to_replace):
        variable_start = line.find(variable_to_remove)
        line_start = line[:variable_start]
        variable_end = variable_start + len(variable_to_remove)
        line_end = line[variable_end:]
        line = line_start + str(variable_to_replace) + line_end
        return line
#End class

#Class with methods to create random data
class generateRandomData:
    MIN_STRING_LENGTH = 3
    MAX_STRING_LENGTH = 15
    SID_VARIABLE = '$SID'
    #Method to generate random string
    def randomString(self):
        symbol_set = '-&!#'
        length = random.randint(self.MIN_STRING_LENGTH, self.MAX_STRING_LENGTH)
        return ''.join(random.choice(string.ascii_uppercase + symbol_set) for x in range(length))

    #Method to generate random SID
    def randomSIDdomain(self):
        beginning_of_SID = "S-1-5-21"
        #create 96-bit random number w/ three subauthorities that receive 32-bit chunks
        num1 = random.getrandbits(32)
        num2 = random.getrandbits(32)
        num3 =random.getrandbits(32)
        string_96_bit = str(num1) + str(num2) + str(num3)
        num_96_bit = int(string_96_bit)
        while (num_96_bit.bit_length()!=96):
            num1 = random.getrandbits(32)
            num2 = random.getrandbits(32)
            num3 =random.getrandbits(32)
            string_96_bit = str(num1) + str(num2) + str(num3)
            num_96_bit = int(string_96_bit)
        return(beginning_of_SID + "-" + str(num1) + "-" + str(num2) + "-" + str(num3))

    def randomRID(self, previous_rids):
        RID = random.randint(1000,9999)
        while RID in previous_rids.values():
            RID = random.randint(1000,9999)
        return RID

    def randomPID(self, previous_pids):
        num = random.randint(0,2499)
        num = num*4
        while num in previous_pids.values():
            num = random.randint(0,2499)
            num = num*4
        return num

    def findNum(self, line, variable_name):
        variable_num = ""
        temp_line = line[line.find(variable_name) + len(variable_name):]
        try:
            for char in temp_line:
                num = int(char)
                variable_num = variable_num + str(num)
        except ValueError:
            pass
        return variable_num

    def findSIDNum(self, line):
        sid_num = line[line.find(self.SID_VARIABLE) + len(self.SID_VARIABLE):line.find(self.SID_VARIABLE) + len(self.SID_VARIABLE) + 1]
        return sid_num

    def findTime(self, line):
        temp_line = line[line.find('"time":') +len('"time":'):]
        start_line = line[:line.find('"time":') +len('"time":')]
        time = line[line.find('"time":')+len('"time":'):temp_line.index(',"') + len(start_line)]
        return time
    #End class

class templateRandomizer:
    #Global Constants
    MACHINE_NAME_VARIABLE = '$HOST'
    USER_NAME_VARIABLE = '$USERNAME'
    SID_VARIABLE = '$SID'
    PID_VARIABLE = '$PID'
    LUSERNAME_VARIABLE = '$LUSERNAME'

    sid_domain = ''

    def __init__(self, template):
        self.template_file = template
        self.is_recreating = False
        self.generator = generateRandomData()
        self.variable_replace = replaceVariables()
        self.last_time = 0
        self.time_offset = 0

        self.PID_dictionary = {}
        self.SID_dictionary = {}
        self.host_dictionary = {}
        self.username_dictionary = {}
        self.lusername_dictionary = {}

        random.seed()

    def recreate_test(self, key_file):
        self.is_recreating = True

        variable_finder = findVariables()
        #Extract data from key file
        for line in key_file:
            line = line[:-1] #Strip newline from end of line
            if line.find("Variable name: ") != -1:
                unknown_variable_name = variable_finder.returnVariable(line, "Variable name: ", ",")
                unknown_generated_value = variable_finder.returnVariableWithNoEnd(line, "Generated value: ")

                #Match variables
                if unknown_variable_name=="Last time":
                    self.last_time = unknown_generated_value
                if unknown_variable_name=="Total time offset":
                    self.time_offset = unknown_generated_value
            if line.find(self.MACHINE_NAME_VARIABLE) != -1:
                host_num = variable_finder.returnVariable(line, self.MACHINE_NAME_VARIABLE, ":")
                host_name = variable_finder.returnVariableWithNoEnd(line, ": ")
                self.host_dictionary[host_num] = host_name

            if line.find(self.USER_NAME_VARIABLE) != -1:
                username_num = variable_finder.returnVariable(line, self.USER_NAME_VARIABLE, ": ")
                username = variable_finder.returnVariableWithNoEnd(line, ": ")
                self.username_dictionary[username_num] = username

            if line.find(self.PID_VARIABLE) != -1:
                pid_num = variable_finder.returnVariable(line, self.PID_VARIABLE, ":")
                pid_value = variable_finder.returnVariableWithNoEnd(line, ": ")
                self.PID_dictionary[pid_num] = pid_value

            if line.find(self.SID_VARIABLE) != -1:
                sid_num = variable_finder.returnVariable(line, self.SID_VARIABLE, ":")
                sid_value = variable_finder.returnVariableWithNoEnd(line, ": ")
                self.SID_dictionary[sid_num] = sid_value
        #End for loop
        key_file.close()

        for key in self.username_dictionary:
            self.lusername_dictionary[key] = (self.username_dictionary[key]).lower()

    """
    Generate a new test but reusing host and sid domain
    Return true if successful; false otherwise
    """
    def generate_test_reuse_host(self, key_file):
        #Generate data
        try:
            #Read first line of file and store time as total offset:
            first_line = self.template_file.readline()
            first_line = first_line.rstrip() #remove \n from end
            self.time_offset = int(first_line)

            #Find current time and set as last time
            self.last_time = int(time.time())
        except:
            return False

        variable_finder = findVariables()
        #Extract data from key file
        for line in key_file:
            line = line[:-1] #Strip newline from end of line
            if line.find(self.MACHINE_NAME_VARIABLE) != -1:
                host_num = variable_finder.returnVariable(line, self.MACHINE_NAME_VARIABLE, ":")
                host_name = variable_finder.returnVariableWithNoEnd(line, ": ")
                self.host_dictionary[host_num] = host_name
            if line.find(self.SID_VARIABLE) != -1:
                sid_num = variable_finder.returnVariable(line, self.SID_VARIABLE, ":")
                sid_value = variable_finder.returnVariableWithNoEnd(line, ": ")
                self.SID_dictionary[sid_num] = sid_value
                self.sid_domain = sid_value[:sid_value.rfind('-')]
            if line.find(self.USER_NAME_VARIABLE) != -1:
                username_num = variable_finder.returnVariable(line, self.USER_NAME_VARIABLE, ": ")
                username = variable_finder.returnVariableWithNoEnd(line, ": ")
                self.username_dictionary[username_num] = username
        return True

    def generate_test(self):
        #Generate data

        try:
            #Read first line of file and store time as total offset:
            first_line = self.template_file.readline()
            first_line = first_line.rstrip() #remove \n from end
            self.time_offset = int(first_line)

            #Find current time and set as last time
            self.last_time = int(time.time())
        except:
            return False


        #Create new SID
        self.sid_domain = self.generator.randomSIDdomain()
        return True

    def write_test_values(self, key_file):
        #Write key information
        key_writer = writeKey()
        key_file.write("Variable name and generated data key: \n\n")
        key_file.write(key_writer.turnToString("Last time", str(self.last_time)))
        key_file.write(key_writer.turnToString("Total time offset", str(self.time_offset)))
        key_file.write(key_writer.dictToString(self.host_dictionary, self.MACHINE_NAME_VARIABLE))
        key_file.write(key_writer.dictToString(self.username_dictionary, self.USER_NAME_VARIABLE))
        key_file.write(key_writer.dictToString(self.SID_dictionary, self.SID_VARIABLE))
        key_file.write(key_writer.dictToString(self.PID_dictionary, self.PID_VARIABLE))

    def next_event(self):
        line = self.template_file.readline()
        if line == '':
            return None

        #Replace variables in template with data
        #Search for and replace key word '$HOST' with new machine name
        if line.find(self.MACHINE_NAME_VARIABLE) != -1:
            num_of_occurences = range(1, line.count(self.MACHINE_NAME_VARIABLE)+1)
            for index in num_of_occurences:
                host_name_num = self.generator.findNum(line, self.MACHINE_NAME_VARIABLE)
                if host_name_num in self.host_dictionary:
                    line = self.variable_replace.removeAndReplaceVariable(line, self.MACHINE_NAME_VARIABLE+str(host_name_num), str(self.host_dictionary[host_name_num]))
                else:
                    random_variable = self.generator.randomString()
                    self.host_dictionary[host_name_num] = random_variable
                    line = self.variable_replace.removeAndReplaceVariable(line, self.MACHINE_NAME_VARIABLE+str(host_name_num), str(self.host_dictionary[host_name_num]))
        #End search for '$HOST'

        if line.find(self.SID_VARIABLE) != -1:
            num_of_occurences = range(1, line.count(self.SID_VARIABLE) + 1)
            for index in num_of_occurences:
                sid_num = self.generator.findSIDNum(line)
                if sid_num in self.SID_dictionary:
                    line = self.variable_replace.removeAndReplaceVariable(line, self.SID_VARIABLE+str(sid_num), str(self.SID_dictionary[sid_num]))
                else:
                    self.SID_dictionary[sid_num] = str(self.sid_domain) + "-" + str(self.generator.randomRID(self.SID_dictionary))
                    line = self.variable_replace.removeAndReplaceVariable(line, self.SID_VARIABLE+str(sid_num), str(self.SID_dictionary[sid_num]))
        #end search for sid

        if line.find(self.USER_NAME_VARIABLE) != -1:
            num_of_occurences = range(1,line.count(self.USER_NAME_VARIABLE)+1)
            for index in num_of_occurences:
                username_num = self.generator.findNum(line, self.USER_NAME_VARIABLE)
                if username_num in self.username_dictionary:
                    line = self.variable_replace.removeAndReplaceVariable(line, self.USER_NAME_VARIABLE+str(username_num), str(self.username_dictionary[username_num]))
                else:
                    self.username_dictionary[username_num] = str(self.generator.randomString())
                    line = self.variable_replace.removeAndReplaceVariable(line, self.USER_NAME_VARIABLE+str(username_num), str(self.username_dictionary[username_num]))
        #end search for username

        #search for lowercase usernames
        if line.find(self.LUSERNAME_VARIABLE) != -1:
            num_of_occurences = range(1, line.count(self.LUSERNAME_VARIABLE)+1)
            for index in num_of_occurences:
                lusername_num = self.generator.findNum(line, self.LUSERNAME_VARIABLE)
                if lusername_num in self.lusername_dictionary:
                    line = self.variable_replace.removeAndReplaceVariable(line, self.LUSERNAME_VARIABLE+str(lusername_num), str(self.lusername_dictionary[lusername_num]))
                else:
                    self.lusername_dictionary[lusername_num] = (self.username_dictionary[lusername_num]).lower()
                    line = self.variable_replace.removeAndReplaceVariable(line, self.LUSERNAME_VARIABLE+str(lusername_num), str(self.lusername_dictionary[lusername_num]))
        #end search for lowercase username

        if line.find('"time":') != -1:
            current_time = self.generator.findTime(line)
            new_time = int(self.last_time) - (int(self.time_offset) - int(current_time))
            line = self.variable_replace.removeAndReplaceVariable(line, str(current_time), str(new_time))
        #end search for time

        #Search for and replace '$PIDint' with new pid number
        if line.find(self.PID_VARIABLE) != -1:
            num_of_occurences = range(1, line.count(self.PID_VARIABLE) + 1)
            for index in num_of_occurences:
                pid_num = self.generator.findNum(line, self.PID_VARIABLE)
                if self.is_recreating:
                    try:
                        pid_value = self.PID_dictionary[pid_num]
                    except KeyError:
                        print("Wrong template was used. Please check input")
                    line = self.variable_replace.removeAndReplaceVariable(line, self.PID_VARIABLE + str(pid_num), pid_value)
                else:
                    if pid_num in self.PID_dictionary:
                        line = self.variable_replace.removeAndReplaceVariable(line, self.PID_VARIABLE+str(pid_num), str(self.PID_dictionary[pid_num]))
                    else:
                        self.PID_dictionary[pid_num] = self.generator.randomPID(self.PID_dictionary)
                        line = self.variable_replace.removeAndReplaceVariable(line, self.PID_VARIABLE+str(pid_num), str(self.PID_dictionary[pid_num]))
        #End searching for PID
        return line

def is_existing_file(parser, arg):
    if os.path.exists(arg):
        return open(arg, 'r')
    else:
        return open(arg, 'w')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Create test from template with random data or data from key")
    parser.add_argument("template", type=argparse.FileType("r"), help="input template file")
    parser.add_argument("new_data_file", type=argparse.FileType("w"), help="output test file")
    parser.add_argument("key", type=lambda x: is_existing_file(parser, x), help="input or output key file")
    parser.add_argument("recreate_test", nargs="*", default=None, help="specify recreate_test to create test from key")
    args = parser.parse_args()

    randomizer = templateRandomizer(args.template)
    if args.recreate_test:
        randomizer.recreate_test(args.key)

    else:
        randomizer.generate_test()

    event = randomizer.next_event()
    while event != None:
        if event != str(randomizer.time_offset) + "\n":
            args.new_data_file.write(event)
        event = randomizer.next_event()

    if not args.recreate_test:
        randomizer.write_test_values(args.key)

    args.new_data_file.close()

