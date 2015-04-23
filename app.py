#!/usr/bin/python
from flask import Flask, jsonify, abort
from flask import make_response
from flask import request
from flask import url_for
from flask.ext.httpauth import HTTPBasicAuth
import httplib
import re
import sendgrid
import requests

app = Flask(__name__)
auth = HTTPBasicAuth()

tasks = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol', 
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web', 
        'done': False
    }
]

class SendEmail:
  """Send emails robustly - if one provider fails, use another."""
  
  to_addresses = []
  subject = ''
  body = ''
  from_address = ''
  
  def __init__(self):
    # to should be an array
    return
    
  def set_from(self, from_address):
    if self.is_valid_email(from_address):
      self.from_address = from_address
      return True
    return False
    
  def set_to(self, to_addresses):
    self.to_addresses = []
    
    addresses = to_addresses.split(',')
    for address in addresses:
      if self.is_valid_email(address):
        self.to_addresses.append(address)
      else:
        return False
    
    return True
    
  def set_subject(self, subject):
    # TODO: check for subject restrictions
    self.subject = subject
    
  def set_body(self, body):
    self.body = body
  
  def is_valid_email(self, email):
    #Alternatively use validate_email python module
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)
    
  def send_email(self):
    send_email = self.send_email_backup()
    if send_email == None:
      return make_error(201, 'Unable to send email')
    return send_email
    
  def send_email_primary(self):
    # TODO: save login credentials in environment file
    sg = sendgrid.SendGridClient('sandscorpio', 'Sendgrid-00', raise_errors=True)
    message = sendgrid.Mail()
    message.add_to(','.join(self.to_addresses)) #check how to support multiple email addresses
    message.set_subject(self.subject)
    message.set_text(self.body)
    message.set_from(self.from_address)
    
    try:
      status, msg = sg.send(message)
    except SendGridClientError:
      return None
    except SendGridServerError:
      return None
      
    return jsonify({'status' : status, 'msg' : msg}), 201 #why 201?
    
  def send_email_backup(self):
    request = requests.post(
            'https://api.mailgun.net/v3/mangobird.mailgun.org/messages',
            auth=("api", 'key-6xnrfd7a38uqa56nfq35ocq4nrqyiis1'),
            data={"from": self.from_address,
                  "to": self.to_addresses,
                  "subject": self.subject,
                  "text": self.body})
                
    if request.status_code != 200:
      # TODO: abort with 402 () or queue message in database and have a background process send those
      return None
    
    return jsonify({'status' : request.status_code, 'msg' : request.text}), 201

@auth.get_password
def get_password(username):
    if username == 'miguel':
        return 'python'
    return None

@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)

@app.route('/')
def index():
    return "Hello, World 2!"
    
@app.route('/todo/api/v1.0/tasks', methods=['GET'])
def get_tasks():
    return jsonify({'tasks': [make_public_task(task) for task in tasks]})
    
@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)
    return jsonify({'task': task[0]})
    
@app.route('/todo/api/v1.0/tasks', methods=['POST'])
def create_task():
    if not request.json or not 'title' in request.json:
        abort(400)
    task = {
        'id': tasks[-1]['id'] + 1,
        'title': request.json['title'],
        'description': request.json.get('description', ""),
        'done': False
    }
    tasks.append(task)
    return jsonify({'task': task}), 201
    
@app.route('/todo/api/v1.0/email', methods=['POST'])
def email():
  #TODO: other field checks. is there a more concise way of checking all in request.json?
  if not request.json:
    return make_error(404, 'expecting json')
  elif not 'subject' in request.json:
    return make_error(404, 'no subject')
  elif not 'from' in request.json:
    return make_error(404, 'no from')
  elif not 'to' in request.json:
    return make_error(404, 'no to')
  elif not 'body' in request.json:
    return make_error(404, 'no body')
    
  from_address = request.json['from']
  to_addresses = request.json['to']
  subject = request.json['subject']
  body = request.json['body']
  
  #TODO: use a singleton
  sender = SendEmail()
  
  if not sender.set_from(from_address):
    # return error json with " from field is not a valid email"
    return make_error(201, 'From field is not a valid address')
    
  if not sender.set_to(to_addresses):
    return make_error(201, 'To field is not valid addresses')
  
  sender.set_subject(subject)
  sender.set_body(body)
  
  return sender.send_email()
  
def make_error(error_code, error):
  return make_response(jsonify({'error_code' : error_code, 'error': error}), 401)
  
def update_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)
    if not request.json:
        abort(400)
    if 'title' in request.json and type(request.json['title']) != unicode:
        abort(400)
    if 'description' in request.json and type(request.json['description']) is not unicode:
        abort(400)
    if 'done' in request.json and type(request.json['done']) is not bool:
        abort(400)
    task[0]['title'] = request.json.get('title', task[0]['title'])
    task[0]['description'] = request.json.get('description', task[0]['description'])
    task[0]['done'] = request.json.get('done', task[0]['done'])
    return jsonify({'task': task[0]})
    


@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)
    tasks.remove(task[0])
    return jsonify({'result': True})
    
def make_public_task(task):
    new_task = {}
    for field in task:
        if field == 'id':
            new_task['uri'] = url_for('get_task', task_id=task['id'], _external=True)
        else:
            new_task[field] = task[field]
    return new_task

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

if __name__ == '__main__':
    app.run(debug=True)