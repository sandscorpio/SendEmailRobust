# SendEmailRobust
Send email robustly : Uber Coding Challenge

This is an API for sending email robustly where two email providers (SendGrid and Mailgun) are used to send emails. If SendGrid is unable to send our email, we fail over to Mailgun and use that service instead.

_API Features_
* JSON in/out
* Versioned URI's so future versions can be written without breaking clients which are relying on previous versions
* All classes and functions are documented
* All user input is validated
* Requests are submitted via POST requests to be consistent with HTTP standards
* Requests are authenticated via username/password
* Note: Sensitive information like API keys for SendGrid and Mailgun and username/password have not been committed to this public repo (constants.py)

_Tech Stack_
* Python with Flask for hosting
* Hosted on Heroku
* Android client app
* SendGrid and Mailgun for sending emails

_My experience_
* I am new to Python so creating the API involved learning Python, Flask, and hosting on Heroku (also for first time). 
* The Client app is an Android app, and I do have good experience there. Details for the app are provided in its README.

_Future_
* Save username/password for requests encrypted in a database. Currently it is cleartext in source code
* Add support for HTML emails and file attachements
* Add unit tests so service can be maintained
* In order to make the service faster, we can fail over faster. For instance, if a request to primary email service (SendGrid)  fails, we can set a flag in a database and use that flag to automatically fail over to backup email service (Mailgun), and skip primary, for a period of time (1 hour, for example). Once the flag expires, we can revert back to using SendGrid. This will keep our API's response time high even if SendGrid is down for a lengthy amount of time. Assuming that SendGrid has a high up-time, this logic will only be used sporadically but will keep our response time very high.




