from datetime import datetime, timedelta
from deap import algorithms
from deap import base
from deap import creator
from deap import tools
from tabulate import tabulate

import random
import numpy

# Hard coded probabilities and generations
CXPB, MUTPB, NGEN = 0.5, 0.2, 50

# Create your models here.
class extGenOptimizer():
    def __init__(self):
        random.seed(128)
        numpy.random.seed(128)

        # Constant variables
        self.examSubjectDuration = timedelta(hours=1) # hour
        # 1 Hour per subject, will be a variable in the future
        # Kept constant initially for simplicity

        # Initializing optimizer
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", numpy.ndarray, fitness=creator.FitnessMax)

        self.toolbox = base.Toolbox()
        
        self.toolbox.register("individual", self.initExamTimetableGenome)
        self.toolbox.register(
            "population", tools.initRepeat, list, self.toolbox.individual)
        
        self.toolbox.register("evaluate", self.evalExamTimetableGenome)
        self.toolbox.register("mate", self.mateExamTimetableGenome)
        self.toolbox.register(
            "mutate", self.mutateExamTimetableGenome, indpb=0.05)
        self.toolbox.register("select", tools.selTournament, tournsize=3)

    # Exam Timetable Genome format: Numpy 2D array
    # Column 0: TimeTable order. Length = Number of subjects
    # Column 1: Rest revision after that subject
    # Last subject exam always have zero revision time as exams are done
    def initExamTimetableGenome(self):
        examTimetableGenome = numpy.zeros([self.subjectLookUpLen, 2])
        examTimetableGenome[:, 0] = range(len(self.subjectLookUp))
        totalRevisionTime = 0
        for idx in range(self.subjectLookUpLen-1):
            tmpRestTime = random.randint(0, self.maxRevisionTime)
            totalRevisionTime = totalRevisionTime + tmpRestTime
            if totalRevisionTime < self.maxRevisionTime:
                examTimetableGenome[idx, 1] = tmpRestTime
            elif totalRevisionTime == self.maxRevisionTime:
                examTimetableGenome[idx, 1] = tmpRestTime
                break
            else:
                examTimetableGenome[idx, 1] = \
                    self.maxRevisionTime - (totalRevisionTime - tmpRestTime)
                break
        if totalRevisionTime < self.maxRevisionTime:
            examTimetableGenome[self.subjectLookUpLen - 2, 1] = \
                examTimetableGenome[self.subjectLookUpLen - 2, 1] + \
                self.maxRevisionTime - totalRevisionTime
        numpy.random.shuffle(examTimetableGenome[:, 0])
        individual = creator.Individual(examTimetableGenome)
        return individual

    # Gets each subject's start time and end time base on revision time
    # Schedule format:
    # idx = 0: subject name
    # idx = 1: start time
    # idx = 2: end time
    # Fixed duration (i.e 1 hour) (self.examSubjectDuration)
    def getSchedule(self, individual):
        schedule = []
        timeSlotCounter = 0
        for idx in range(0, self.subjectLookUpLen):
            if idx == 0:
                startTime = self.timeSlots[0][0]
            else:
                revisionTime = timedelta(hours=individual[idx-1][1])
                startTime = lastEndTime + revisionTime
            endTime = startTime + self.examSubjectDuration

            if endTime > self.timeSlots[timeSlotCounter][1]:
                extraRevisionTime = startTime - \
                    self.timeSlots[timeSlotCounter][1]
                while True:
                    timeSlotCounter = timeSlotCounter + 1
                    timeSlotStart = self.timeSlots[timeSlotCounter][0]
                    timeSlotEnd = self.timeSlots[timeSlotCounter][1]
                    timeSlotDuration = timeSlotEnd - timeSlotStart
                    if timeSlotDuration <= extraRevisionTime:
                        if timeSlotCounter >= len(self.timeSlots):
                            print('fail')
                            return 0 # Punishment
                        else:
                            extraRevisionTime = extraRevisionTime - \
                                timeSlotDuration
                    else:
                        startTime = timeSlotStart + extraRevisionTime
                        endTime = startTime + self.examSubjectDuration
                        break
            lastEndTime = endTime
            schedule.append([
                    self.subjectLookUp[int(individual[idx][0])],
                    startTime, 
                    endTime
                    ])
        return schedule

    # Gets all the revision time based on the student's examination list
    # and the exam schedule generated
    def getRevisionTimeFromSchedule(self, record, schedule):
        revisionTimeArray = []
        firstSubjectExamined = False
        studentSubjectList = record[1:]
        for idx in range(0, self.subjectLookUpLen):
            if self.subjectLookUp[idx] in studentSubjectList:
                if firstSubjectExamined:
                    revisionTimeArray.append(
                        (schedule[idx][1] - lastEndTime).total_seconds() 
                        / 3600)
                    lastEndTime = schedule[idx][2]
                else:
                    firstSubjectExamined = True
                    lastEndTime = schedule[idx][2]
        if len(revisionTimeArray) == 0:
            return [float('inf')]
        else:
            return revisionTimeArray

    # Generate schedule base on order and revision time
    # For each student, sum up their revision time
    # Average all student's revision time
    def evalExamTimetableGenome(self, individual):
        schedule = self.getSchedule(individual)
        minRevisionTime = float('inf')
        for student in self.studentRecord:
            tmpRevisionTime = self.getRevisionTimeFromSchedule(student, 
                                                               schedule)
            if min(tmpRevisionTime) < minRevisionTime:
                minRevisionTime = min(tmpRevisionTime)
        return minRevisionTime, # Comma is important

    # Copy child 1 and 2 as individual 1 and 2
    # Take two points
    # Extract a section from individual1
    # Remove the elements from in the section from child 2 
    # and add section at beginning of child 2
    # Same procedure for individual 2 and child 1
    def mateExamTimetableGenome(self, individual1, individual2):
        child1 = individual1
        child2 = individual2

        cxpoint1 = random.randint(0, self.subjectLookUpLen-1)
        cxpoint2 = random.randint(0, self.subjectLookUpLen-1)

        if cxpoint1 == cxpoint2:
            return (child1, child2)
        elif cxpoint1 > cxpoint2:
            tmp = cxpoint1
            cxpoint1 = cxpoint2
            cxpoint2 = tmp

        tmpList1 = list(individual1[:, 0])
        tmpSection1 = list(individual1[cxpoint1: cxpoint2, 0])

        tmpList2 = list(individual2[:, 0])
        tmpSection2 = list(individual2[cxpoint1: cxpoint2, 0])

        for item in tmpSection2:
            tmpList1.remove(item)
        child1[:, 0] = tmpSection2 + tmpList1        

        for item in tmpSection1:
            tmpList2.remove(item)
        child2[:, 0] = tmpSection1 + tmpList2

        return (child1, child2)

    # Find two random indices and swap two subjects
    # Find two random indices and swap two revision times, last one is fixed
    def mutateExamTimetableGenome(self, individual, indpb):
        # Swap two subjects
        cxpoint1 = random.randint(0, self.subjectLookUpLen-1)
        cxpoint2 = random.randint(0, self.subjectLookUpLen-1)
        
        tmp = individual[cxpoint1, 0]
        individual[cxpoint1, 0] = individual[cxpoint2, 0]
        individual[cxpoint1, 0] = tmp

        # Swap two revision time, last one fixed, not allowed for swapping
        cxpoint1 = random.randint(0, self.subjectLookUpLen-2)
        cxpoint2 = random.randint(0, self.subjectLookUpLen-2)
        
        tmp = individual[cxpoint1, 1]
        individual[cxpoint1, 1] = individual[cxpoint2, 1]
        individual[cxpoint1, 1] = tmp

        # For the two rest times, mutate their times by +/- 1
        if individual[cxpoint1, 1] > 0:
            individual[cxpoint1, 1] = individual[cxpoint1, 1] - 1
            individual[cxpoint2, 1] = individual[cxpoint2, 1] + 1
        elif individual[cxpoint2, 1] > 0:
            individual[cxpoint2, 1] = individual[cxpoint2, 1] - 1
            individual[cxpoint1, 1] = individual[cxpoint1, 1] + 1

        return individual

    # Print results including all information
    def printResult(self, individual):
        result = [['Subject', 'Revision Time', 'Start Time', 'End Time'], 
                  ['-'*20] * 4]
        schedule = self.getSchedule(individual)
        for idx in range(self.subjectLookUpLen):
            tmp = []
            tmp.append(self.subjectLookUp[int(individual[idx][0])])
            if idx < self.subjectLookUpLen -1:
                tmp.append((schedule[idx+1][1]-schedule[idx][2])
                           .total_seconds() / 3600)
            else:
                tmp.append(0)
            tmp.append(schedule[idx][1])
            tmp.append(schedule[idx][2])
            result.append(tmp)
        print(tabulate(result))
        obj1 = self.evalExamTimetableGenome(individual)
        print("Min Revision Time = %f" % (obj1))

    # Run otpimizer
    def run(self, verbose = False):
        # Data validation

        # Data formation
        # All subjects are assumed to last for an hour for simplicity
        # This constraint will be opened up later on
        self.subjectLookUp = []
        for student in self.studentRecord:
            for subject in student[1:]:
                if subject not in self.subjectLookUp:
                    self.subjectLookUp.append(subject)
        self.subjectLookUpLen = len(self.subjectLookUp)
        # Calculate total number of hours
        self.totalNumHours = 0
        for ts in self.timeSlots:
            # Integer division, rounded down
            self.totalNumHours += (ts[1] - ts[0]).seconds / 3600
        self.maxRevisionTime = self.totalNumHours - len(self.subjectLookUp) * 1
        
        pop = self.toolbox.population(n=300)

        if verbose:
            print("Start of evolution")
    
        # Evaluate the entire population
        fitnesses = list(map(self.toolbox.evaluate, pop))
        for ind, fit in zip(pop, fitnesses):
            ind.fitness.values = fit
    
        if verbose:
            print("  Evaluated %i individuals" % len(pop))
        
        # Begin the evolution
        for g in range(NGEN):
            if verbose:
                print("-- Generation %i --" % g)
        
            # Select the next generation individuals
            offspring = self.toolbox.select(pop, len(pop))
            # Clone the selected individuals
            offspring = list(map(self.toolbox.clone, offspring))
    
            # Apply crossover and mutation on the offspring
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < CXPB:
                    self.toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values

            for mutant in offspring:
                if random.random() < MUTPB:
                    self.toolbox.mutate(mutant)
                    del mutant.fitness.values
    
            # Evaluate the individuals with an invalid fitness
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
        
            if verbose:
                print("  Evaluated %i individuals" % len(invalid_ind))
        
            # The population is entirely replaced by the offspring
            pop[:] = offspring
            
            if verbose:
                # Gather all the fitnesses in one list and print the stats
                fits = [ind.fitness.values[0] for ind in pop]
        
                length = len(pop)
                mean = sum(fits) / length
                sum2 = sum(x*x for x in fits)
                std = abs(sum2 / length - mean**2)**0.5
            
                print("  Min %s" % min(fits))
                print("  Max %s" % max(fits))
                print("  Avg %s" % mean)
                print("  Std %s" % std)            
            
                print("-- End of (successful) evolution --")

        self.best_ind = tools.selBest(pop, 1)[0]
        if verbose:
            self.printResult(self.best_ind)
        return self.getSchedule(self.best_ind)
            
if __name__ == "__main__":
    t = extGenOptimizer()
    t.timeSlots = [
        [datetime(2015, 11, 11, 9), datetime(2015, 11, 11, 12)],
        [datetime(2015, 11, 12, 9), datetime(2015, 11, 12, 12)],
        [datetime(2015, 11, 14, 9), datetime(2015, 11, 14, 12)],
        ]
    t.studentRecord = [
        ["A", "Chinese", "English"],
        ["B", "Chinese", "English", "Math"],
        ["C", "Chinese", "English", "Math"],
        ]         
    t.run(verbose=True)
