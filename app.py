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
  cc_addresses = []
  bcc_addresses = []
  subject = ''
  body = ''
  from_address = ''
  
  def __init__(self):
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
    Set TO field for email.
    Must be an array of one or more valid email addresses
    Returns True on success, False otherwise
    """
    if SendEmail.verify_email_addresses(to_addresses):
      self.to_addresses = to_addresses
      return True
    return False
    
  def set_cc(self, cc_addresses):
    """
    Set CC field for email.
    Must be an array of one or more valid email addresses
    Returns True on success, False otherwise
    """
    if SendEmail.verify_email_addresses(cc_addresses):
      self.cc_addresses = cc_addresses
      return True
    return False
    
  def set_bcc(self, bcc_addresses):
    """
    Set BCC field for email.
    Must be an array of one or more valid email addresses
    Returns True on success, False otherwise
    """
    if SendEmail.verify_email_addresses(bcc_addresses):
      self.bcc_addresses = bcc_addresses
      return True
    return False
    
  @staticmethod
  def verify_email_addresses(addresses):
    """
    Helper static method to check if all addresses are valid
    """
    for address in addresses:
      if not SendEmail.is_valid_email(address):
        return False
        
    return True
    
  @staticmethod
  def is_valid_email(email):
    """
    Helper static method to check if given email is a valid email address
    Returns True on success, False otherwise
    """
    #TODO: Alternatively use validate_email python module
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)
    
  def set_subject(self, subject):
    """
    Set subject
    Returns True on success, False otherwise
    """
    self.subject = subject
    return True
    
  def set_body(self, body):
    """
    Set body
    Returns True on success, False otherwise
    """
    self.body = body if body else ' '
    return True
    
  def send_email(self):
    """
    Send email robustly. Fail over to backup service if primary service fails
    Returns True on success, False otherwise
    """
    if not (self.to_addresses and self.from_address):
      raise StandardError('TO/FROM must be set before calling send_email()')

    is_email_sent = self.send_email_primary()
    
    if not is_email_sent:
      # fail over to backup email provider
      is_email_sent = self.send_email_backup()
      if not is_email_sent:
        # both primary and backup email providers failed
        return False
    
    return True
    
  def send_email_primary(self):
    """
    Send email using primary service (Sendgrid)
    Returns True on success, False otherwise
    """
    sg = sendgrid.SendGridClient(constants.SENDGRID_USERNAME, constants.SENDGRID_PASSWORD, raise_errors=True)
    message = sendgrid.Mail()
    message.add_to(self.to_addresses)
    if self.cc_addresses:
      message.add_cc(self.cc_addresses)
    if self.bcc_addresses:
      message.add_cc(self.bcc_addresses)
    message.set_subject(self.subject)
    message.set_text(self.body)
    message.set_from(self.from_address)
    
    try:
      status, msg = sg.send(message)
    except sendgrid.SendGridClientError:
      return False
    except sendgrid.SendGridServerError:
      return False
      
    return True
    
  def send_email_backup(self):
    """
    Send email using backup service (Mailgun)
    Returns 201 on success, None on failure
    """
    
    data = {"from": self.from_address,
                  "to": ','.join(self.to_addresses), #pass TO field as comma separated email addresses
                  "subject": self.subject,
                  "text": self.body}
    if self.cc_addresses:
      data['cc'] = ','.join(self.cc_addresses)
    if self.bcc_addresses:
      data['bcc'] = ','.join(self.bcc_addresses)
      
    request = requests.post(
                constants.MAILGUN_DOMAIN,
                auth=("api", constants.MAILGUN_KEY),
                data=data)
                
    if request.status_code != httplib.OK:
      return False
    
    return True

app = Flask(__name__)
auth = HTTPBasicAuth()

@auth.get_password
def get_password(username):
    if username == constants.API_USERNAME:
        return constants.API_PASSWORD
    return None

@auth.error_handler
def unauthorized():
    return make_error(httplib.UNAUTHORIZED, 'Unauthorized access')

@app.route('/')
def index():
    return "Hello, Heroku!"
    
@app.route('/todo/api/v1.0/email', methods=['POST'])
@auth.login_required
def email():
  """
  Send email robustly.
  All fields should be passed in JSON. Expecting:
   - subject : subject (can be empty)
   - from : email_address
   - to : array of email_addresses 
   - body : body (can be empty)
   - cc : array of email_addresses  optional
   - bcc : array of email_addresses optional
   
  Returns OK on success 
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
  cc = request.json['cc'] if 'cc' in request.json else ''
  bcc = request.json['bcc'] if 'bcc' in request.json else ''
  
  sender = SendEmail()
  if not sender.set_from(from_address):
    return make_error(httplib.NOT_ACCEPTABLE, 'From field is not a valid address')
  if not sender.set_to(to_addresses):
    return make_error(httplib.NOT_ACCEPTABLE, 'To field is not valid addresses')
  if not sender.set_subject(subject):
    return make_error(httplib.NOT_ACCEPTABLE, 'Subject is not valid')
  if not sender.set_body(body):
    return make_error(httplib.NOT_ACCEPTABLE, 'Body is not valid')
  if cc and not sender.set_cc(cc):
    return make_error(httplib.NOT_ACCEPTABLE, 'CC is not valid addresses')
  if bcc and not sender.set_bcc(bcc):
    return make_error(httplib.NOT_ACCEPTABLE, 'BCC is not valid addresses')
  
  if sender.send_email():
    # successfully sent email
    return jsonify({'status' : httplib.OK, 'msg' : 'success'}), httplib.OK
  
  return make_error(httplib.SERVICE_UNAVAILABLE, 'Sorry, unable to send email currently. Please try again later')
  
def make_error(response_code, error):
  return make_response(jsonify({'status' : response_code, 'error': error}), response_code)

if __name__ == '__main__':
    app.run(debug=True)
