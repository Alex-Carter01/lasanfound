import webapp2
import jinja2
import logging
import cgi
import os
import time
import string
import sys
import urllib2
import urllib
import re
import httplib
import json
import imghdr
from datetime import datetime, timedelta
from google.appengine.api import app_identity
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext import ndb
from google.appengine.ext.webapp import blobstore_handlers
import smtplib
from email.mime.text import MIMEText

## see http://jinja.pocoo.org/docs/api/#autoescaping
def guess_autoescape(template_name):
 if template_name is None or '.' not in template_name:
  return False
  ext = template_name.rsplit('.', 1)[1]
  return ext in ('xml', 'html', 'htm')

JINJA_ENVIRONMENT = jinja2.Environment(
 autoescape=guess_autoescape,     ## see http://jinja.pocoo.org/docs/api/#autoxscaping
 loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
 extensions=['jinja2.ext.autoescape'])

class Handler(webapp2.RequestHandler):
 def write(self, *items):    
  self.response.write(" : ".join(items))

 def render_str(self, template, **params):
  tplt = JINJA_ENVIRONMENT.get_template('templates/'+template)
  return tplt.render(params)

 def render(self, template, **kw):
  self.write(self.render_str(template, **kw))

 def render_json(self, d):
  json_txt = json.dumps(d, indent = 3, sort_keys = True)
  self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
  self.write(json_txt)

#Model for the item objects
class Item(db.Model):
 title = db.StringProperty()
 description = db.StringProperty()
 location = db.StringProperty()
 picture = db.BlobProperty()
 created = db.DateTimeProperty(auto_now_add = True)

class Home(Handler):
 def get(self):
  logging.info("********** WelcomePage GET **********")
  items = db.GqlQuery("SELECT * FROM Item ORDER BY created DESC limit 10")
  self.render("home.html", items=items)

class About(Handler):
  def get(self):
    self.render("about.html")

  def post(self):
    logging.info("this is russells bet")
    ip = self.request.remote_addr
    """with open(textfile, 'rb') as fp:
      msg = MIMEText(fp.read())
      msg['Subject'] = 'The contents of %s' % textfile
      msg['From'] = "spamrebo@gmail.com"
      msg['To'] = "alexjcarter@gmail.com"
    s = smtplib.SMTP('localhost')
    s.sendmail("spamrebo@gmail.com", ["alexjcarter@gmail.com"], msg.as_string())
    s.quit()"""
    self.render("about.html", ip=ip, congrats="AYY CONGRATS U WERE THE FIRST TO DO IT")

class NewItem(Handler):
 def get(self):
  logging.info("******** New Item GET ******")
  upload_url = blobstore.create_upload_url('/upload')
  #this needs to iclude a blob array
  self.render("newitem.html", upload_url=upload_url)

 def post(self):
  #need to add error hanling for a file too  large
  logging.info("******** New Item POST *******")
  upload_url = blobstore.create_upload_url('/upload')
  title = self.request.get("title")
  desc = self.request.get("description")
  location = self.request.get("location")
  picture = self.request.get("file")
  img_type = imghdr.what(None, picture)
  img_type = str(img_type)
  supportedtypes = ['png', 'jpeg', 'gif', 'tiff', 'bmp']
  if(title==""):
    logging.info("error, submitted blank title")
    titleError="*Please Add a Title*"
    self.render("newitem.html", titleError=titleError, descData=desc, locData=location, upload_url=upload_url)
  elif(img_type not in supportedtypes):
    logging.info("error, invalid file type: "+img_type)
    fileError="*Not Supported Filetype*<br><br>Supported Types: " + ", ".join(supportedtypes)
    self.render("newitem.html", fileError=fileError, descData=desc, locData=location, upload_url=upload_url, titleData=title)
  else:
    logging.info("no errors, posting item")
    it = Item(title=title, description=desc, location=location, picture=db.Blob(picture))
    it.put()
    #item_id = it.key().id()
    time.sleep(0.1)
    self.redirect('/')

class PermItem(Handler):
  def get(self, item_id):
    logging.info("entering the permalink for each lost item")
    logging.info("id: "+str(item_id))
    id_int = int(item_id)
    item = Item.get_by_id(id_int)
    self.render("item.html", item=item)

  def post(self, item_id):
    id_int = int(item_id)
    item = Item.get_by_id(id_int)
    logging.info("item: "+str(item.key()))
    logging.info("this is if they want to claim an item")
    con = httplib.HTTPSConnection("www.google.com")
    con.request("POST", "/recaptcha/api/siteverify", urllib.urlencode({"secret": "6LdVQTQUAAAAAEla2hBTZfXSiBOiaGUjYPVcbzIg", "response": self.request.get("g-recaptcha-response"), "remoteip": self.request.remote_addr}), {"Content-Type": "application/x-www-form-urlencoded"})
    response = con.getresponse()
    data = response.read()
    success = json.loads(data)['success']
    if success:
      #this delete action isnt working
      item.delete()
      logging.info("key: "+str(item))
      time.sleep(0.1)
      self.redirect('/')
    else:
      self.render("item.html", item=item, error="Please complete reCaptcha")

class ImgHandler(Handler):
  def get(self, img_id):
    logging.info("img handler get")
    item = Item.get_by_id(int(img_id))
    if item.picture:
      logging.info(item.title)
      self.response.headers['Content-Type']="image"
      self.response.out.write(item.picture)
    else:
      self.error(404)

application = webapp2.WSGIApplication([
 ('/', Home),
 ('/new', NewItem), 
 ('/about', About),
 (r'/img/(\d+)', ImgHandler),
 (r'/item/(\d+)', PermItem),
 (r'/\S+', Home),#who needs 404 errors?
], debug=True)