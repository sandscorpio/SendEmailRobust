#!/usr/bin/python
import httplib
import re
import sendgrid
import requests
from flask import Flask, jsonify, abort
from flask import make_response, request, url_for
from flask.ext.httpauth import HTTPBasicAuth
import constants #contains our private keys 

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
  """
  Send emails robustly - if primary email service fails, use backup service to send email
  File attachments are not supported
  HTML is not supported
  """
  
  to_addresses = []
  subject = ''
  body = ''
  from_address = ''
  
  def __init__(self):
    # to should be an array
    return
    
  def set_from(self, from_address):
    """
    Set the from address. 
    From address must be a valid email address
    Returns True on success, False otherwise
    """
    if self.is_valid_email(from_address):
      self.from_address = from_address
      return True
    return False
    
  def set_to(self, to_addresses):
    """
    Set to field for email.
    Must be one or more valid email addresses separated by commas
    Returns True on success, False otherwise
    """
    self.to_addresses = []
    
    addresses = to_addresses.split(',')
    for address in addresses:
      if self.is_valid_email(address):
        self.to_addresses.append(address)
      else:
        return False
    
    return True
    
  def set_subject(self, subject):
    """
    Set subject
    Returns True on success, False otherwise
    """
    # TODO: check for subject restrictions
    self.subject = subject
    return True
    
  def set_body(self, body):
    """
    Set body
    Returns True on success, False otherwise
    """
    self.body = body
    return True
  
  def is_valid_email(self, email):
    """
    Helper function to check if given email is a valid email address
    Returns True on success, False otherwise
    """
    #TODO: Alternatively use validate_email python module
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)
    
  def send_email(self):
    """
    Send email robustly. Fail over to backup service if primary service fails
    Returns 201 on success, 400 on failure
    """
    # TODO: check from/to/subject/body have been set
    send_email = self.send_email_primary()
    if send_email == None:
      # fail over to backup email provider
      send_email = self.send_email_backup()
      if send_email == None:
        return make_error(201, 'Unable to send email')
    return send_email
    
  def send_email_primary(self):
    """
    Send email using primary service (Sendgrid)
    Returns 201 on success, None on failure
    """
    # TODO: save login credentials in environment file
    sg = sendgrid.SendGridClient(constants.SENDGRID_USERNAME, constants.SENDGRID_PASSWORD, raise_errors=True)
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
    """
    Send email using backup service (Mailgun)
    Returns 201 on success, None on failure
    """
    request = requests.post(
            constants.MAILGUN_DOMAIN,
            auth=("api", constants.MAILGUN_KEY),
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