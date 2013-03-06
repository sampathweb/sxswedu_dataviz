# Main Python file that connects to InBloom and fetches Data
# Once all the data is retrieved, index.html is rendered for display
#
from flask import Flask, redirect, url_for, request, jsonify, render_template
import requests
import numpy as np
import pandas as pd
import simplejson as json

params = {
    'base_url': 'https://api.sandbox.slcedu.org',
    'redirect_uri' : 'http://127.0.0.1:5000/oauth',
    'client_id' : 'CLIENT ID',
    'client_secret': 'SECRET KEY',
    'oauth_code': '',
    'req_code_url': '/api/oauth/authorize',
    'req_token_url': '/api/oauth/token'
    }

SECRET_KEY = 'SWSXEDU_SECRET_KEY'
DEBUG = True

# setup flask
app = Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY

@app.route('/')
def index():
    slc_code_url = params['base_url']  \
                + params['req_code_url'] \
                + '?response_type=code' \
                + '&client_id=' + params['client_id'] \
                + '&redirect_uri=' + url_for('oauth', _external=True)
    return redirect(slc_code_url)

@app.route('/oauth')
def oauth():
    params['oauth_code'] = request.args.get('code')
    if request.args.get('code') == None:
        return redirect(url_for('index'))
    else:
        slc_token_url = params['base_url']  \
                 + params['req_token_url']  \
                 + '?grant_type=authorization_code'  \
                 + '&client_id=' + params['client_id'] \
                 + '&client_secret=' + params['client_secret'] \
                 + '&code=' + request.args.get('code') \
                 + '&redirect_uri=' + url_for('oauth', _external=True)

    oauth_token = requests.get(slc_token_url)
    if oauth_token.status_code != 200:
        return redirect(url_for('index'))
    access_token = oauth_token.content[17:].strip('}"')
    headers = {'Authorization': 'bearer ' + access_token}
    students_jdata = requests.get('https://api.sandbox.inbloom.org/api/rest/v1.1/students', headers=headers)
    students = []
    for student_jdata in students_jdata.json():
        student = {}
        student['studentUniqueStateId'] = student_jdata.get('studentUniqueStateId', 0)
        if student['studentUniqueStateId'] == 0:
            continue
        student_name = student_jdata.get('name')
        if student_name:
            student['firstName'] = student_name.get('firstName')
            student['middleName'] = student_name.get('middleName', '')
            student['lastSurname'] = student_name.get('lastSurname', '')
        student['sex'] = student_jdata.get('sex')
        student_links = student_jdata.get('links')
        for link in student_links:
            if link.get('rel') == 'getAttendances':
                student[link['rel']] = link.get('href')
        students.append(student)
    students_col = list(students[0].keys())
    stud_df = pd.DataFrame(students, columns=students_col)

    students_atd = []
    for i in range(len(stud_df)):
        atd_jdata = requests.get(stud_df.ix[i].get('getAttendances'), headers=headers).json()[0]
        for key in atd_jdata:
            if key == 'schoolYearAttendance':
                school_attend = atd_jdata[key]
                for j in range(len(school_attend)):
                    for attend_event in school_attend[j]['attendanceEvent']:
                        student = {}
                        student['studentUniqueStateId'] = stud_df.ix[i]['studentUniqueStateId']
                        student['firstName'] = stud_df.ix[i]['firstName']
                        student['middleName'] = stud_df.ix[i]['middleName']
                        student['lastSurname'] = stud_df.ix[i]['lastSurname']
                        student['schoolYear'] = school_attend[j]['schoolYear']
                        student['date'] = attend_event['date']
                        student['event'] = attend_event['event']
                        student['reason'] = attend_event.get('reason', '')
                        if student['event'] == 'In Attendance':
                            student['attendance'] = 1
                        else:
                            student['attendance'] = 0
                        students_atd.append(student)


#    students_col = list(students_atd[0].keys())
#    students_atd_df = pd.DataFrame(students_atd, columns=students_col)
#    students_atd_df.to_csv('student_attendance.csv', index=False)
    return render_template('main.html', students_attend=students_atd)

@app.route('/templates/<iframe_html>')
def iframe(iframe_html):
    return render_template(iframe_html)

app.run()