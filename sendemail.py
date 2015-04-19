#!/usr/bin/python
from flask import Flask, jsonify, abort
from flask import make_response
from flask import request
from flask import url_for
from flask.ext.httpauth import HTTPBasicAuth
import sendgrid
import requests
import re
import httplib
import constants

class SendEmail:
  """Send emails robustly - if one provider fails, use another."""
  
  to_addresses = []
  subject = ''
  body = ''
  from_address = ''
  
  def __init__(self):
    # to should be an array
    return
    
  def set_to_addresses(to):
    self.to = []
    
    addresses = to.split(',')
    for address in addresses:
      if is_valid_email(to):
        self.to.append(address)
      else:
        return False
    
    return True
    
  def set_from_addresses(from_address):
    if is_valid_email(from_address):
      self.from_address = from_address
      return True
      
    return False
    
  def set_subject(subject):
    # TODO: check for subject restrictions
    self.subject = subject
    
  def set_body(body):
    self.body = body
    
  def is_valid_email(email):
    #Alternatively use validate_email python module
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)
    
  #TODO: support flipping primary/backup if primary fails (save a boolean in a text file) -- we will have to check this flag on every request but that should be neglible compared to sending emails
  def send_email():
    send_email = self.send_email_primary()
    if send_email == Nil:
      send_email = self.send_email_backup()
    return send_email
    
  def send_email_primary():
    # TODO: save login credentials in environment file
    sg = sendgrid.SendGridClient(constants.SENDGRID_USERNAME, constants.SENDGRID_PASSWORD, raise_errors=True)
    message = sendgrid.Mail()
    message.add_to(','.self.to)
    message.set_subject(self.subject)
    message.set_text(self.body)
    message.set_from(self.from_address)
    
    try:
      status, msg = sg.send(message)
    except SendGridClientError:
      return Nil
    except SendGridServerError:
      return Nil
      
    return jsonify({'status' : status, 'msg' : msg}), 201 #why 201?
    
  def send_email_backup():
    request = requests.post(
            constants.MAILGUN_DOMAIN,
            auth=("api", constants.MAILGUN_KEY),
            data={"from": "Amit <amit.aggarwal.x@gmail.com>",
                  "to": ["amit.aggarwal.x@gmail.com"],
                  "subject": "Hello",
                  "text": "Testing some Mailgun awesomness!"})
                
    if request.status_code != httplib.OK:
      # TODO: abort with 402 () or queue message in database and have a background process send those
      return jsonify({'status' : request.status_code, 'body' : request.text})
    
    return jsonify({'status' : request.status_code, 'body' : request.text})
    
  #define setters for the other fields with error checking
  
app = Flask(__name__)

@app.route('/')
def index():
    return "Hello, World 1!"
    
@app.route('/sendemail/api/v1.0/send', methods=['POST'])
def send():
    if not request.json:
      abort(httplib.BAD_REQUEST)
    elif not 'subject' in request.json:
      abort(httplib.BAD_REQUEST)
    elif not 'from' in request.json:
      abort(httplib.BAD_REQUEST)
    #TODO: other field checks. is there a more concise way of checking all in request.json?    
    
    from_address = request.json['from']
    to_addresses = request.json['to']
    subject = request.json['subject']
    body = request.json['body']
    
    #TODO: use a singleton
    sender = SendEmail()
    sender.set_from_address(from_address)
    sender.setTo(to_addresses)
    sender.set_subject(subject)
    sender.set_body(body)
    
    return sender.sendEmail()

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

if __name__ == '__main__':
    app.run(debug=True)