from __future__ import print_function
import copy
import os
import subprocess
import csv
from TVgen import TestVector_A, TestVector_B, TestVector_C, TestVector_D, TestVector_E 

# Function List:
# 0. getFaults: gets the faults from the file
# 1. genFaultList: generates all of the faults and prints them to a file
# 2. netRead: read the benchmark file and build circuit netlist
# 3. gateCalc: function that will work on the logic of each gate
# 4. inputRead: function that will update the circuit dictionary made in netRead to hold the line values
# 5. basic_sim: the actual simulation
# 6. main: The main function

#gets all of the faults from the file
def getFaults(faultFile):
    #opens the file
    inFile = open(faultFile, "r")

    faults = []

    #goes line by line and adds the faults to arrays
    for line in inFile:
        # Do nothing else if empty lines, ...
        if (line == "\n"):
            continue
        # ... or any comments
        if (line[0] == "#"):
            continue
        
        line = line.replace("\n", "")
        data = []
        for _ in range(5):
            data.append(False)
        data.append(line.split("-"))

        faults.append(data)
    inFile.close()
    return faults

# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: Neatly prints the Circuit Dictionary:
def printCkt (circuit):
    print("INPUT LIST:")
    for x in circuit["INPUTS"][1]:
        print(x + "= ", end='')
        print(circuit[x])

    print("\nOUTPUT LIST:")
    for x in circuit["OUTPUTS"][1]:
        print(x + "= ", end='')
        print(circuit[x])

    print("\nGATE list:")
    for x in circuit["GATES"][1]:
        print(x + "= ", end='')
        print(circuit[x])
    print()


# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: Reading in the Circuit gate-level netlist file:
def netRead(netName):
    # Opening the netlist file:
    netFile = open(netName, "r")

    # temporary variables
    inputs = []     # array of the input wires
    outputs = []    # array of the output wires
    gates = []      # array of the gate list
    inputBits = 0   # the number of inputs needed in this given circuit


    # main variable to hold the circuit netlist, this is a dictionary in Python, where:
    # key = wire name; value = a list of attributes of the wire
    circuit = {}

    # Reading in the netlist file line by line
    for line in netFile:

        # NOT Reading any empty lines
        if (line == "\n"):
            continue

        # Removing spaces and newlines
        line = line.replace(" ","")
        line = line.replace("\n","")

        # NOT Reading any comments
        if (line[0] == "#"):
            continue

        # @ Here it should just be in one of these formats:
        # INPUT(x)
        # OUTPUT(y)
        # z=LOGIC(a,b,c,...)

        # Read a INPUT wire and add to circuit:
        if (line[0:5] == "INPUT"):
            # Removing everything but the line variable name
            line = line.replace("INPUT", "")
            line = line.replace("(", "")
            line = line.replace(")", "")

            # Format the variable name to wire_*VAR_NAME*
            line = "wire_" + line

            # Error detection: line being made already exists
            if line in circuit:
                msg = "NETLIST ERROR: INPUT LINE \"" + line + "\" ALREADY EXISTS PREVIOUSLY IN NETLIST"
                print(msg + "\n")
                return msg

            # Appending to the inputs array and update the inputBits
            inputs.append(line)

            # add this wire as an entry to the circuit dictionary
            circuit[line] = ["INPUT", line, False, 'U']

            inputBits += 1
            #print(line)
            #print(circuit[line])
            continue

        # Read an OUTPUT wire and add to the output array list
        # Note that the same wire should also appear somewhere else as a GATE output
        if line[0:6] == "OUTPUT":
            # Removing everything but the numbers
            line = line.replace("OUTPUT", "")
            line = line.replace("(", "")
            line = line.replace(")", "")

            # Appending to the output array
            outputs.append("wire_" + line)
            continue

        # Read a gate output wire, and add to the circuit dictionary
        lineSpliced = line.split("=") # splicing the line at the equals sign to get the gate output wire
        gateOut = "wire_" + lineSpliced[0]

        # Error detection: line being made already exists
        if gateOut in circuit:
            msg = "NETLIST ERROR: GATE OUTPUT LINE \"" + gateOut + "\" ALREADY EXISTS PREVIOUSLY IN NETLIST"
            print(msg+"\n")
            return msg

        # Appending the dest name to the gate list
        gates.append(gateOut)

        lineSpliced = lineSpliced[1].split("(") # splicing the line again at the "("  to get the gate logic
        logic = lineSpliced[0].upper()


        lineSpliced[1] = lineSpliced[1].replace(")", "")
        terms = lineSpliced[1].split(",")  # Splicing the the line again at each comma to the get the gate terminals
        # Turning each term into an integer before putting it into the circuit dictionary
        terms = ["wire_" + x for x in terms]

        # add the gate output wire to the circuit dictionary with the dest as the key
        circuit[gateOut] = [logic, terms, False, 'U']
        #print(gateOut)
        #print(circuit[gateOut])

    # now after each wire is built into the circuit dictionary,
    # add a few more non-wire items: input width, input array, output array, gate list
    # for convenience
    
    circuit["INPUT_WIDTH"] = ["input width:", inputBits]
    circuit["INPUTS"] = ["Input list", inputs]
    circuit["OUTPUTS"] = ["Output list", outputs]
    circuit["GATES"] = ["Gate list", gates]

    #print("\n bookkeeping items in circuit: \n")
    #print(circuit["INPUT_WIDTH"])
    #print(circuit["INPUTS"])
    #print(circuit["OUTPUTS"])
    #print(circuit["GATES"])


    return circuit


# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: calculates the output value for each logic gate
def gateCalc(circuit, node):
    
    # terminal will contain all the input wires of this logic gate (node)
    terminals = list(circuit[node][1])  

    # If the node is an Buffer gate output, solve and return the output
    if circuit[node][0] == "BUFF":
        if circuit[terminals[0]][3] == '0':
            circuit[node][3] = '0'
        elif circuit[terminals[0]][3] == '1':
            circuit[node][3] = '1'
        elif circuit[terminals[0]][3] == "U":
            circuit[node][3] = "U"
        else:  # Should not be able to come here
            return -1
        return circuit

    # If the node is an Inverter gate output, solve and return the output
    if circuit[node][0] == "NOT":
        if circuit[terminals[0]][3] == '0':
            circuit[node][3] = '1'
        elif circuit[terminals[0]][3] == '1':
            circuit[node][3] = '0'
        elif circuit[terminals[0]][3] == "U":
            circuit[node][3] = "U"
        else:  # Should not be able to come here
            return -1
        return circuit

    # If the node is an AND gate output, solve and return the output
    elif circuit[node][0] == "AND":
        # Initialize the output to 1
        circuit[node][3] = '1'
        # Initialize also a flag that detects a U to false
        unknownTerm = False  # This will become True if at least one unknown terminal is found

        # if there is a 0 at any input terminal, AND output is 0. If there is an unknown terminal, mark the flag
        # Otherwise, keep it at 1
        for term in terminals:  
            if circuit[term][3] == '0':
                circuit[node][3] = '0'
                break
            if circuit[term][3] == "U":
                unknownTerm = True

        if unknownTerm:
            if circuit[node][3] == '1':
                circuit[node][3] = "U"
        return circuit

    # If the node is a NAND gate output, solve and return the output
    elif circuit[node][0] == "NAND":
        # Initialize the output to 0
        circuit[node][3] = '0'
        # Initialize also a variable that detects a U to false
        unknownTerm = False  # This will become True if at least one unknown terminal is found

        # if there is a 0 terminal, NAND changes the output to 1. If there is an unknown terminal, it
        # changes to "U" Otherwise, keep it at 0
        for term in terminals:
            if circuit[term][3] == '0':
                circuit[node][3] = '1'
                break
            if circuit[term][3] == "U":
                unknownTerm = True
                break

        if unknownTerm:
            if circuit[node][3] == '0':
                circuit[node][3] = "U"
        return circuit

    # If the node is an OR gate output, solve and return the output
    elif circuit[node][0] == "OR":
        # Initialize the output to 0
        circuit[node][3] = '0'
        # Initialize also a variable that detects a U to false
        unknownTerm = False  # This will become True if at least one unknown terminal is found

        # if there is a 1 terminal, OR changes the output to 1. Otherwise, keep it at 0
        for term in terminals:
            if circuit[term][3] == '1':
                circuit[node][3] = '1'
                break
            if circuit[term][3] == "U":
                unknownTerm = True

        if unknownTerm:
            if circuit[node][3] == '0':
                circuit[node][3] = "U"
        return circuit

    # If the node is an NOR gate output, solve and return the output
    if circuit[node][0] == "NOR":
        # Initialize the output to 1
        circuit[node][3] = '1'
        # Initialize also a variable that detects a U to false
        unknownTerm = False  # This will become True if at least one unknown terminal is found

        # if there is a 1 terminal, NOR changes the output to 0. Otherwise, keep it at 1
        for term in terminals:
            if circuit[term][3] == '1':
                circuit[node][3] = '0'
                break
            if circuit[term][3] == "U":
                unknownTerm = True
        if unknownTerm:
            if circuit[node][3] == '1':
                circuit[node][3] = "U"
        return circuit

    # If the node is an XOR gate output, solve and return the output
    if circuit[node][0] == "XOR":
        # Initialize a variable to zero, to count how many 1's in the terms
        count = 0

        # if there are an odd number of terminals, XOR outputs 1. Otherwise, it should output 0
        for term in terminals:
            if circuit[term][3] == '1':
                count += 1  # For each 1 bit, add one count
            if circuit[term][3] == "U":
                circuit[node][3] = "U"
                return circuit

        # check how many 1's we counted
        if count % 2 == 1:  # if more than one 1, we know it's going to be 0.
            circuit[node][3] = '1'
        else:  # Otherwise, the output is equal to how many 1's there are
            circuit[node][3] = '0'
        return circuit

    # If the node is an XNOR gate output, solve and return the output
    elif circuit[node][0] == "XNOR":
        # Initialize a variable to zero, to count how many 1's in the terms
        count = 0

        # if there is a single 1 terminal, XNOR outputs 0. Otherwise, it outputs 1
        for term in terminals:
            if circuit[term][3] == '1':
                count += 1  # For each 1 bit, add one count
            if circuit[term][3] == "U":
                circuit[node][3] = "U"
                return circuit

        # check how many 1's we counted
        if count % 2 == 1:  # if more than one 1, we know it's going to be 0.
            circuit[node][3] = '1'
        else:  # Otherwise, the output is equal to how many 1's there are
            circuit[node][3] = '0'
        return circuit

    # Error detection... should not be able to get at this point
    return circuit[node][0]


# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: Updating the circuit dictionary with the input line, and also resetting the gates and output lines
def inputRead(circuit, line):
    # Checking if input bits are enough for the circuit
    if len(line) < circuit["INPUT_WIDTH"][1]:
        return -1

    # Getting the proper number of bits:
    line = line[(len(line) - circuit["INPUT_WIDTH"][1]):(len(line))]

    # Adding the inputs to the dictionary
    # Since the for loop will start at the most significant bit, we start at input width N
    i = circuit["INPUT_WIDTH"][1] - 1
    inputs = list(circuit["INPUTS"][1])
    # dictionary item: [(bool) If accessed, (int) the value of each line, (int) layer number, (str) origin of U value]
    for bitVal in line:
        bitVal = bitVal.upper() # in the case user input lower-case u
        circuit[inputs[i]][3] = bitVal # put the bit value as the line value
        circuit[inputs[i]][2] = True  # and make it so that this line is accessed

        # In case the input has an invalid character (i.e. not "0", "1" or "U"), return an error flag
        if bitVal != "0" and bitVal != "1" and bitVal != "U":
            return -2
        i -= 1 # continuing the increments

    return circuit

# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: the actual simulation #
def basic_sim(circuit):
    # QUEUE and DEQUEUE
    # Creating a queue, using a list, containing all of the gates in the circuit
    queue = list(circuit["GATES"][1])
    i = 1

    while True:
        i -= 1
        # If there's no more things in queue, done
        if len(queue) == 0:
            break

        # Remove the first element of the queue and assign it to a variable for us to use
        curr = queue[0]
        queue.remove(curr)

        # initialize a flag, used to check if every terminal has been accessed
        term_has_value = True
        
        # Check if the terminals have been accessed
        for term in circuit[curr][1]:
            if not circuit[term][2]:
                term_has_value = False
                break

        if term_has_value:
            
            #checks to make sure the gate output has not already been set
            if(circuit[curr][2] == False):
                circuit = gateCalc(circuit, curr)

            circuit[curr][2] = True

            # ERROR Detection if LOGIC does not exist
            if isinstance(circuit, str):
                print(circuit)
                return circuit

        else:
            # If the terminals have not been accessed yet, append the current node at the end of the queue
            queue.append(curr)

    return circuit


def plot():
    plotProcess = subprocess.Popen("gnuplot p2plot.gpl", shell = True)
    os.waitpid(plotProcess.pid, 0)


# -------------------------------------------------------------------------------------------------------------------- #
# FUNCTION: Main Function
def main():
    # **************************************************************************************************************** #
    # NOTE: UI code; Does not contain anything about the actual simulation

    #NOTE: Not sure what this is used for says unused
    # Used for file access
    #script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in

    

    #gets user choice
    while True:
        userChoice = 0
        print("\nChoose what you would like to do (1 or 2): \n")
        print("1: Test Vector Generation\n")
        print("2: Fault Coverage Simulation\n")
        userInput = input()
        if userInput =="":
            print("\nPlease Enter a value\n")
            break
        else: 
            userChoice = int(userInput)
            if(userChoice >= 1 & userChoice <= 2):
                break
            else:
                print("\nChoice not valid. Please enter a valid choice.\n")

    circuit = netRead("circ.bench")


    # keep an initial (unassigned any value) copy of the circuit for an easy reset
    newCircuit = circuit


    if(userChoice == 1):
        #get seed
        while True:
            print("\nOption 1: Test Vector Generation.")
            seedVal = 0
            print("Choose a seed in [1, 255]: ", end = "")
            userInput = input()
            if userInput =="":
                print("\nERROR: No Seed Chosen\n")
            else: 
                seedVal = int(userInput)
                if(seedVal >= 1 & seedVal <= 255):
                    break
                else:
                    print("\nERROR: Value not within range.\n")
            
        
        print("\ninput file: circ.bench")
        print("ouptut files: TV_A.txt, TV_B.txt, TV_C.txt, TV_D.txt, TV_E.txt")

        print("\nProcessing...\n")
        print("TV_A...", end = ""),
        TestVector_A(circuit["INPUT_WIDTH"][1], seedVal)
        print("done\nTV_B...", end = ""),
        TestVector_B(circuit["INPUT_WIDTH"][1], seedVal)
        print("done\nTV_C...", end = ""),
        TestVector_E(circuit["INPUT_WIDTH"][1], seedVal)
        print("done\nTV_D...", end = ""),
        TestVector_D(circuit["INPUT_WIDTH"][1], seedVal)
        print("done\nTV_C...", end = ""),
        TestVector_C(circuit["INPUT_WIDTH"][1], seedVal)
        print("done\n\nDone.")

    elif(userChoice == 2):

        #get batch size
        while True:
            print("\nOption 2: Fault Coverage Simulation.")
            batchSize = 1
            print("Choose a batch size in [1, 10]: ", end = "")
            userInput = input()
            if userInput =="":
                print("\nERROR: please enter a batch size\n")
            else: 
                batchSize = int(userInput)
                if(batchSize >= 1 & batchSize <= 10):
                    break
                else:
                    print("\nERROR: not a valid integer\n")


        #gets the faults that need to be tested
        faults = getFaults("f_list.txt")

        print("\ninput files: circ.bench, f_list.txt, TV_A.txt, TV_B.txt, TV_C.txt, TV_D.txt, TV_E.txt")
        print("output file: f_cvg.csv")

        print("\nProcessing...\n")
        # Note: UI code;
        # **************************************************************************************************************** #

        inputFiles = []
        inputFiles.append(open("TV_A.txt", "r"))
        inputFiles.append(open("TV_B.txt", "r"))
        inputFiles.append(open("TV_C.txt", "r"))
        inputFiles.append(open("TV_D.txt", "r"))
        inputFiles.append(open("TV_E.txt", "r"))

        #get seed value and moves the file cursor to the second line
        seedVal = ""
        for x in inputFiles:
            seedVal = x.readline()

        seedVal = seedVal.replace("#seed: ", "")
        seedVal = format(int(seedVal), "08b")

        totalFaults = len(faults)
        totalDetected = [0, 0, 0, 0, 0]

        csvFile = open("f_cvg.csv", "w")

        writer = csv.writer(csvFile)
        writer.writerow(["Batch #", "A", "B", "C", "D", "E", "seed = " + seedVal, "batch size = " + str(batchSize)])

        # Runs the simulator for each line of the input file
        for batch in range(25):
            print("Batch: " + str(batch +1) + "...", end = "")
            for fileIndex in range(5):
                for _ in range(batchSize):
                    
                    #reads the newline
                    line = inputFiles[fileIndex].readline()
        
                    # Initializing output variable each input line
                    output = ""

                    # Do nothing else if empty lines, ...
                    if (line == "\n"):
                        continue
                    # ... or any comments
                    if (line[0] == "#"):
                        continue

                    # Removing the the newlines at the end
                    line = line.replace("\n", "")

                    # Removing spaces
                    line = line.replace(" ", "")

                    circuit = inputRead(circuit, line)

                    if circuit == -1:
                        print("INPUT ERROR: INSUFFICIENT BITS")
                        # After each input line is finished, reset the netList
                        circuit = newCircuit
                        print("...move on to next input\n")
                        continue
                    elif circuit == -2:
                        print("INPUT ERROR: INVALID INPUT VALUE/S")
                        # After each input line is finished, reset the netList
                        circuit = newCircuit
                        print("...move on to next input\n")
                        continue


                    circuit = basic_sim(circuit)

                    for y in circuit["OUTPUTS"][1]:
                        if not circuit[y][2]:
                            output = "NETLIST ERROR: OUTPUT LINE \"" + y + "\" NOT ACCESSED"
                            break
                        output = str(circuit[y][3]) + output

                    for faultLine in faults:
                        #skips fault if already detected
                        if(faultLine[fileIndex] == True):
                            continue

                        #creates a copy of the circuit to be used for fault testing
                        faultCircuit = copy.deepcopy(circuit)

                        for key in faultCircuit:
                            if (key[0:5]=="wire_"):
                                faultCircuit[key][2] = False
                                faultCircuit[key][3] = 'U'
                        
                        #sets up the inputs for the fault circuit
                        faultCircuit = inputRead(faultCircuit, line)

                        #handles stuck at faults
                        if(faultLine[5][1] == "SA"):
                            for key in faultCircuit:
                                if(faultLine[5][0] == key[5:]):
                                        faultCircuit[key][2] = True
                                        faultCircuit[key][3] = faultLine[5][2]

                        #handles in in stuck at faults by making a new "wire"
                        elif(faultLine[5][1] == "IN"):
                            faultCircuit["faultWire"] = ["FAULT", "NONE", True, faultLine[5][4]]

                            #finds the input that needs to be changed to the fault line
                            for key in faultCircuit:
                                if(faultLine[5][0] == key[5:]):
                                    inputIndex = 0
                                    for gateInput in faultCircuit[key][1]:
                                        if(faultLine[5][2] == gateInput[5:]):
                                            faultCircuit[key][1][inputIndex] = "faultWire"
                                        
                                        inputIndex += 1
                        
                        #runs Circuit Simulation
                        faultCircuit = basic_sim(faultCircuit)
                        
                        #gets the output
                        faultOutput = ""
                        for y in faultCircuit["OUTPUTS"][1]:
                            if not faultCircuit[y][2]:
                                faultOutput = "NETLIST ERROR: OUTPUT LINE \"" + y + "\" NOT ACCESSED"
                                break
                            faultOutput = str(faultCircuit[y][3]) + faultOutput

                        #checks to see if the fault was detected
                        if(output != faultOutput):
                            faultLine[fileIndex] = True
                            totalDetected[fileIndex] += 1
                
                    for key in circuit:
                        if (key[0:5]=="wire_"):
                            circuit[key][2] = False
                            circuit[key][3] = 'U'

            writer.writerow([batch + 1, totalDetected[0]/totalFaults*100, totalDetected[1]/totalFaults*100, totalDetected[2]/totalFaults*100, totalDetected[3]/totalFaults*100, totalDetected[4]/totalFaults*100])
            print("done")

        for x in inputFiles:
            x.close()
        csvFile.close()

        print("\nDone.")
        
        plot()


if __name__ == "__main__":
    main()

