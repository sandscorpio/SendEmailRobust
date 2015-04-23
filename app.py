#!/usr/bin/python
import re
import httplib
from flask import Flask, jsonify, abort
from flask import make_response, request, url_for
from flask.ext.httpauth import HTTPBasicAuth
import sendgrid
import requests
import constants #contains our private keys 

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
  
  @staticmethod
  def is_valid_email(email):
    """
    Helper static method to check if given email is a valid email address
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
    is_email_sent = self.send_email_primary()
    
    if not is_email_sent:
      # fail over to backup email provider
      is_email_sent = self.send_email_backup()
      if not is_email_sent:
        # both primary and backup email providers failed
        return make_error(httplib.SERVICE_UNAVAILABLE, 'Sorry, unable to send email currently. Please try again later')
    
    return jsonify({'status' : httplib.OK, 'msg' : 'success'}), httplib.OK
    
  def send_email_primary(self):
    """
    Send email using primary service (Sendgrid)
    Returns 201 on success, None on failure
    """
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
      
    return True
    
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
                
    if request.status_code != httplib.OK:
      return None
    
    return jsonify({'status' : request.status_code, 'msg' : request.text}), httplib.ACCEPTED

app = Flask(__name__)
auth = HTTPBasicAuth()

@auth.get_password
def get_password(username):
    if username == 'miguel':
        return 'python'
    return None

@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)
    
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/')
def index():
    return "Hello, World 2!"
    
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
  """
  Send email robustly.
  All fields should be passed in JSON. Expecting:
   - subject : subject
   - from : email_address
   - to : email_address(es) (comma separated)
   - body : body
   
  Returns 201 on success, 400 on failure   
  """
  if not request.json:
    return make_error(httplib.BAD_REQUEST, 'Expecting JSON-encoded values')
  elif not 'subject' in request.json:
    return make_error(httplib.BAD_REQUEST, 'Missing subject')
  elif not 'from' in request.json:
    return make_error(httplib.BAD_REQUEST, 'Missing from')
  elif not 'to' in request.json:
    return make_error(httplib.BAD_REQUEST, 'Missing to')
  elif not 'body' in request.json:
    return make_error(httplib.BAD_REQUEST, 'Missing body')
    
  from_address = request.json['from']
  to_addresses = request.json['to']
  subject = request.json['subject']
  body = request.json['body']
  
  #TODO: use a singleton
  sender = SendEmail()
  
  if not sender.set_from(from_address):
    return make_error(httplib.NOT_ACCEPTABLE, 'From field is not a valid address')
  if not sender.set_to(to_addresses):
    return make_error(httplib.NOT_ACCEPTABLE, 'To field is not valid addresses')
  if not sender.set_subject(subject):
    return make_error(httplib.NOT_ACCEPTABLE, 'Subject is not valid')
  if not sender.set_body(body):
    return make_error(httplib.NOT_ACCEPTABLE, 'Body is not valid')
  
  return sender.send_email()
  
def make_error(response_code, error):
  return make_response(jsonify({'response_code' : response_code, 'error': error}), response_code)

if __name__ == '__main__':
    app.run(debug=True)