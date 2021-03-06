from flask import jsonify
from datetime import datetime, timedelta
from extGenOptimizer import extGenOptimizer
import json

# Config
inputDateTimeFormat = "%Y-%m-%d,%H:%M"
dateFormat = "%Y-%m-%d"
timeFormat = "%Y-%m-%dT%H:%M:%S"

def main(request):
     # Set CORS headers for the preflight request
    if request.method == 'OPTIONS':
        # Allows GET requests from any origin with the Content-Type
        # header and caches preflight response for an 3600s
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }

        return ('', 204, headers)
    # Load data from body
    if not request.json:
        abort(400)
    body = request.json
    print(body)
    print(body['timeSlots'])
    timeSlots = []
    for t in body['timeSlots']:
        startTime = datetime.strptime(t['start'], inputDateTimeFormat)
        endTime = datetime.strptime(t['end'], inputDateTimeFormat)
        timeSlots.append([startTime, endTime])
    studentRecord = body['studentRecord']
    # Use optimizer
    t = extGenOptimizer()
    t.timeSlots = timeSlots
    t.studentRecord = studentRecord
    print(t.studentRecord)
    # Return results
    schedule = t.run(verbose=True)
    examEvents = convertScheduleToExamEvents(schedule, timeSlots)
    result = parseResult(examEvents)
    resp = jsonify(result)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

def getExamEvent(title, start, end):
    examEvent = {}
    examEvent['title'] = title
    examEvent['start'] = start
    examEvent['end'] = end
    examEvent['description'] = ''
    return examEvent

def getBackgroundTimeSlots(start, end):
    backgroundTimeSlot = {}
    backgroundTimeSlot['id'] = 'timeSlots'
    backgroundTimeSlot['start'] = start
    backgroundTimeSlot['end'] = end
    backgroundTimeSlot['rendering'] = 'background'
    backgroundTimeSlot['description'] = ''
    return backgroundTimeSlot

def convertScheduleToExamEvents(schedule, timeSlots):
    examEvents = []
    for item in schedule:
        examEvents.append(getExamEvent(item[0], item[1], item[2]))
    for item in timeSlots:
        examEvents.append(getBackgroundTimeSlots(item[0], item[1]))
    return examEvents

def parseResult(examEvents):
    ret = {}
    # Sort the exam events
    examEvents = sorted(examEvents, key=lambda e: e['start'])
    # Get first exam date
    firstExamTime = datetime.strftime(examEvents[0]['start'], dateFormat)
    ret['defaultDate'] = firstExamTime    
    # Put exam events into event JSON object
    for e in examEvents:
        e['start'] = datetime.strftime(e['start'], timeFormat)
        e['end'] = datetime.strftime(e['end'], timeFormat)
        e['description'] = str(e['description'])
    ret['events'] = examEvents
    return ret