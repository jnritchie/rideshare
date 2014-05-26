# This is actually the development one.
# lutherrideshare.appspot key: ABQIAAAAg9WbCE_zwMIRW7jDFE_3ixS0LiYWImofzW4gd3oCqtkHKt0IaBT-STdq-gdH-mW2_ejMPXqxnfJjgw

# This has the app id of ridesharebeta   and is also on ridesharebeta.appspot.com
# rideshare.luther.edu key:  ABQIAAAAg9WbCE_zwMIRW7jDFE_3ixQ2JlMNfqnGb2qqWZtmZLchh1TSjRS0zuchuhlR8g4tlMGrjg34sNmyjQ
#!/usr/bin/env python2.5
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import webapp2

from google.appengine.dist import use_library
use_library('django', '1.2')

choice = "facebook"

import wsgiref.handlers
import datetime
from datetime import date
from django.utils import simplejson
from google.appengine.api import mail

##from django.core import serializers

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
import facebook

#from appengine_django.models import BaseModel
from google.appengine.ext import db
if choice != "facebook":
   from google.appengine.api import users
else:
   import nateusers as users
   from nateusers import LoginHandler, LogoutHandler, BaseHandler, FBUser

from pygeocoder import Geocoder

import logging
import urllib
import random
import os.path

from model import *


MAP_APIKEY=""
FROM_EMAIL_ADDR="ridesharedecorah@gmail.com"
NOTIFY_EMAIL_ADDR="ridesharedecorah@gmail.com"
rideshareWebsite = "http://www.decorahrideshare.com"

early_late_strings = { "0": "Early", "1": "Late" }
part_of_day_strings = { "0": "Morning", "1": "Afternoon", "2": "Evening" }

mycollege = College(name = "Luther College",
    address = "700 College Drive Decorah,IA",
    lat = 43.313059, lng = -91.799501,
    appId = "193298730706524",
    appSecret = "44d7cce20524dc91bf7694376aff9e1d")

aquery = db.Query(College)
#if aquery.count()==0:
    # development site
    # mycollege = College(name = "Luther College",
    #     address = "700 College Drive Decorah,IA",
    #     lat = 43.313059, lng = -91.799501,
    #     appId = "193298730706524",
    #     appSecret = "44d7cce20524dc91bf7694376aff9e1d")
    # live site   
    # college = College(name ="Luther College", address= "700 College Drive Decorah,IA", lat =43.313059, lng=-91.799501, appId="284196238289386",appSecret="07e3ea3ffda4aa08f8c597bccd218e75")   
    # college = College(name= "LaCrosse University", address = "1725 State Street, La Crosse, WI", lat=43.812834, lng=-91.229022,appId="193298730706524",appSecret="44d7cce20524dc91bf7694376aff9e1d")
    # college = College(name="Decorah", address="Decorah, IA", appId="177023452434948", appSecret="81a9f8776108bd1f216970823458533d", lat=43.303306, lng=-91.785709)
    #mycollege.put()
 

class MainHandler(BaseHandler):
  def get(self):

    user = FBUser.get_by_key_name(self.current_user.id)
    aquery = db.Query(College)
    mycollege= aquery.get()

    eventsList = []
    circles = []
    for item in user.circles:
        query = db.Query(Event)
        query.filter("ToD > ", datetime.date.today())
        query.filter("circle =",str(item))
        event_list = query.fetch(limit=100)
        logging.debug(event_list)
        for event in event_list:
          eventsList.append(event.to_dict())
        circles.append(Circle.get_by_id(int(item)))
    path = os.path.join(os.path.dirname(__file__), 'templates/main.html')
    self.response.out.write(str(template.render(path, {
            'event_list': eventsList,
            'circles' : circles,
            'college':mycollege,
            'logout':'/auth/logout',
            'nick':self.current_user.nickname()
            })))

    
class MapHandler(BaseHandler):

    def get(self):
        query = db.Query(Ride)
        query.filter("ToD > ", datetime.date.today())
        logging.debug(self.request.get("circle"))
        query.filter("circle = ",self.request.get("circle"))
        ride_list = query.fetch(limit=100)
        
        aquery = db.Query(College)
        mycollege= aquery.get()
        user = self.current_user
        logging.debug(users.create_logout_url("/"))
        greeting = ''
        logout = ''
        #if user:
        #    greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>) Go to your <a href='/home'>Home Page</a>" %
        #          (user.nickname(), users.create_logout_url("/")))
        #    logout = users.create_logout_url("/")
        #    logging.debug(logout)
        #else:
        #    self.redirect('/auth/login')
        #    return
        
        logging.debug(mycollege.address)
        path = os.path.join(os.path.dirname(__file__), 'templates/map.html')
        self.response.out.write(str(template.render(path, {
            'ride_list': ride_list, 
            'greeting' : greeting,
            'college': mycollege,
            'address': mycollege.address,
            'nick' : user.nickname(),
            'user':user.id,
            'logout':'/auth/logout',
            'mapkey':MAP_APIKEY,
            })))


class RideQueryHandler(BaseHandler):
    """
    Parse and process requests for rides
    returns json
    """

    def get(self):
        """
        Arguments:
        - `self`:

        The query may be filtered by after date, and before date.  Expect to get the dates
        in the form YYYY-MM-DD
        """
        logger = logging.getLogger('MySite')
        logger.info(str(self.request))
        # Create a query object
        allRides = Ride.all()
        # Check to see if the browser side provided us with before/after dates
        after_date = self.request.get('after')
        before_date = self.request.get("before")
        # If there is an after date then limit the rides to those after the date
        # using the filter method
        if after_date:
            y,m,d = after_date.split('-')
            allRides.filter('ToD >= ',datetime.date(int(y),int(m),int(d)))


        if before_date:
            y,m,d = before_date.split("-")
            allRides.filter('ToD <=',datetime.date(int(y),int(m),int(d)))
        logging.debug(self.request.get("circle"))
        allRides.filter('circle =',self.request.get("circle"))
        logging.debug("after %s before %s", after_date, before_date)
    
        if self.request.get("event"):
            allRides.filter('event =',self.request.get("event"))
        else:
            allRides.filter('event =',None)
        # Now put together the json result to send back to the browser.
        json = simplejson.dumps([r.to_dict() for r in allRides])
        self.response.headers.add_header('content-type','application/json')
        self.response.out.write(json)
        logging.debug('end get')
    
class EventQueryHandler(BaseHandler):
    """
    Parse and process requests for events
    returns json
    """

    def get(self):
        """
        Arguments:
        - `self`:

        The query may be filtered by after date, and before date.  Expect to get the dates
        in the form YYYY-MM-DD
        """
        # Create a query object
        allEvents = Event.all()

        # Check to see if the browser side provided us with before/after dates
        after_date = self.request.get('after')
        before_date = self.request.get("before")
        # If there is an after date then limit the rides to those after the date
        # using the filter method
        if after_date:
            y,m,d = after_date.split('-')
            allEvents.filter('ToD >= ',datetime.date(int(y),int(m),int(d)))


        if before_date:
            y,m,d = before_date.split("-")
            allEvents.filter('ToD <=',datetime.date(int(y),int(m),int(d)))
        logging.debug(self.request.get("circle"))
        allEvents.filter('circle =',self.request.get("circle"))
        logging.debug("after %s before %s", after_date, before_date) 

        # Now put together the json result to send back to the browser.
        json = simplejson.dumps([e.to_dict() for e in allEvents])
        self.response.headers.add_header('content-type','application/json')
        self.response.out.write(json)
        logging.debug('end get')

class NewEventRideHandler(BaseHandler):
    """
    For new Event Rides
    """

    def get(self):

        user = self.current_user
        newRide = Ride()
        maxp = self.request.get("maxp")
        inumber = self.request.get("contact")
        if not "-" in inumber:
            number = inumber[0:3]+'-'+inumber[3:6]+'-'+inumber[6:]
        else:
            number = inumber
        newRide.contact = number

        isDriver = self.request.get("isDriver")
        if isDriver.lower() == "false":
            isDriver = False
        else:
            isDriver = True
        
        aquery = db.Query(College)
        mycollege= aquery.get()


        lat = float(self.request.get("lat")) * (random.random() * (1.000001-.999999) + 1.000001)
        lng = float(self.request.get("lng")) * (random.random() * (1.000001-.999999) + 1.000001)
        checked = self.request.get("toLuther")
        if checked == 'true':
          newRide.start_point_title = self.request.get("from")
          newRide.start_point_lat = lat
          newRide.start_point_long = lng
          newRide.destination_title = mycollege.name
          newRide.destination_lat = mycollege.lat
          newRide.destination_long = mycollege.lng
        elif checked == 'false':
          newRide.start_point_title = mycollege.name
          newRide.start_point_lat = mycollege.lat
          newRide.start_point_long = mycollege.lng
          newRide.destination_title = self.request.get("to")
          newRide.destination_lat = lat
          newRide.destination_long = lng             
        y = int(self.request.get("year"))
        m = int(self.request.get("month"))
        d = int(self.request.get("day"))
        time = self.request.get("time")
        early_late_value = int(self.request.get("earlylate"))

        part_of_day = ''
        newRide.event = self.request.get("eventId")
        newRide.time = time
        newRide.part_of_day = part_of_day
        logger = logging.getLogger('MySite')
        logger.info(str(m))
        newRide.ToD = datetime.date(int(y),int(m),int(d))

        newRide.max_passengers = int(maxp)
        newRide.num_passengers = 0
        newRide.passengers = []


        if isDriver:
            newRide.driver = user.id
            newRide.drivername = FBUser.get_by_key_name(user.id).nickname()
        else:
            user_name = user.id
            passenger = Passenger()
            passenger.name = user_name
            passenger.fullname = FBUser.get_by_key_name(user.id).nickname()
            logging.debug(FBUser.get_by_key_name(user.id).nickname())
            passenger.contact = number
            passenger.location = newRide.destination_title
            passenger.lat = lat
            passenger.lng = lng
            pass_key = passenger.put()
            newRide.passengers.append(pass_key)
            newRide.num_passengers = 1

        newRide.comment = self.request.get("comment")
        newRide.circle = self.request.get("circleType")
        ride_key = newRide.put()
        
        if not isDriver:
            passenger.ride = ride_key
            passenger.put()

        query = db.Query(Ride)
        query.filter("ToD > ", datetime.date.today())
        query.filter("circle = ",self.request.get("circle"))
        ride_list = query.fetch(limit=100)
        self.sendRideEmail(newRide)
        greeting = ''
        if user:
            greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>) Go to your <a href='/home'>Home Page</a>" %
                  (user.nickname(), users.create_logout_url("/")))
        message = 'Your ride has been created!'
        path = os.path.join(os.path.dirname(__file__), 'templates/map.html')
        self.response.out.write(str(template.render(path, {
            'ride_list': ride_list, 
            'greeting': greeting,
            'message': message,
            'mapkey' : MAP_APIKEY,
            })))

    def sendRideEmail(self,ride):
      
        driverName = None
        passengerName = None
        subject = "New Ride "
        if ride.driver:
            if self.current_user.loginType == "google":
               to = self.current_user.email
               logging.debug(to)
            driverName = self.current_user.nickname()
        else:
            p = db.get(ride.passengers[0])
            logging.debug(p)
            #if self.current_user.loginType == "google":
               #to = p.email
            passengerName = self.current_user.nickname()
            
        sender = FROM_EMAIL_ADDR
        announceAddr = NOTIFY_EMAIL_ADDR
        if driverName:
            subject += "Announcement"
            body = """
A new ride is being offered.  %s is offering a ride from %s to %s on %s.
Please go to %s if you want to join this ride.

Thanks,

The Rideshare Team
""" % (driverName,ride.start_point_title,ride.destination_title,ride.ToD,rideshareWebsite)
        else:
            subject += "Request"
            body = """
A new ride request has been posted.  %s is looking for a ride from %s to %s on %s.
If you are able to take this person in your car, please go to %s
        
Thanks,

The Rideshare Team
""" % (passengerName,ride.start_point_title,ride.destination_title,ride.ToD,rideshareWebsite)

        if self.current_user.loginType == "facebook":
          logging.debug(self.current_user.access_token)
          graph = facebook.GraphAPI(self.current_user.access_token)
          graph.put_object("me", "feed", message=body)
          #pageGraph = facebook.GraphAPI("AAAECeZAfUaeoBAHYuYZC8NN9djZAlA6PZBpJnCWvZCxZBnDeEWQcdj3YuBZCWEJbPZA1E35QiCHqYmCxXsNkqT82tn67nMitdirfjxvZBAZBCfWzRKbCFZAHFZCH")
          #pageGraph.put_object("144494142268497","feed",message=body)
    
class NewRideHandler(BaseHandler):
    """
    For new Rides
    """

    def get(self):
        """
        Called when a new ride needs to be added to the database.
        Probably with all of this data it should be done as a form post.
        
        Arguments:
        - `self`:
        Web Arguments:
        - max_passengers
        - num_passengers
        - driver
        - start_point_title
        - start_point_lat
        - start_point_long
        - destination_title
        - destination_lat
        - destination_long
        - part_of_day
        - ToD
        - contact
        - ridecomments
        - driver
        """
        user = self.current_user
        newRide = Ride()
        maxp = self.request.get("maxp")
        inumber = self.request.get("contact")
        if not "-" in inumber:
            number = inumber[0:3]+'-'+inumber[3:6]+'-'+inumber[6:]
        else:
            number = inumber
        newRide.contact = number

        isDriver = self.request.get("isDriver")
        if isDriver.lower() == "false":
            isDriver = False
        else:
            isDriver = True
        
        aquery = db.Query(College)
        mycollege= aquery.get()
        """ # For testing
        latlng = ['41.517658', '-95.452065']
        lat = float(latlng[0])
        lng = float(latlng[1])
        """
        lat = float(self.request.get("lat")) * (random.random() * (1.000001-.999999) + 1.000001)
        lng = float(self.request.get("lng")) * (random.random() * (1.000001-.999999) + 1.000001)
        checked = self.request.get("toLuther")
        if checked == 'true':
          newRide.start_point_title = self.request.get("from")
          newRide.start_point_lat = lat
          newRide.start_point_long = lng
          newRide.destination_title = mycollege.name
          newRide.destination_lat = mycollege.lat
          newRide.destination_long = mycollege.lng
        elif checked == 'false':
          newRide.start_point_title = mycollege.name
          newRide.start_point_lat = mycollege.lat
          newRide.start_point_long = mycollege.lng
          newRide.destination_title = self.request.get("to")
          newRide.destination_lat = lat
          newRide.destination_long = lng             
        y = int(self.request.get("year"))
        m = int(self.request.get("month")) + 1
        d = int(self.request.get("day"))
        early_late_value = int(self.request.get("earlylate"))
        part_of_day_value = int(self.request.get("partofday"))
        # TODO:  replace this logic with the global dictionaries.
        part_of_day = ''
        if early_late_value == 0:
          part_of_day += 'Early '
        else:
          part_of_day += 'Late '
        if part_of_day_value == 0:
          part_of_day += 'Morning'
        elif part_of_day_value == 1:
          part_of_day += 'Afternoon'
        else:
          part_of_day += 'Evening'
        newRide.part_of_day = part_of_day
        newRide.ToD = datetime.date(int(y),int(m),int(d))

        newRide.max_passengers = int(maxp)
        newRide.num_passengers = 0
        newRide.passengers = []


        if isDriver:
            newRide.driver = user.id
            newRide.drivername = FBUser.get_by_key_name(user.id).nickname()
        else:
            user_name = user.id
            passenger = Passenger()
            passenger.name = user_name
            passenger.fullname = FBUser.get_by_key_name(user.id).nickname()
            logging.debug(FBUser.get_by_key_name(user.id).nickname())
            passenger.contact = number
            passenger.location = newRide.destination_title
            passenger.lat = lat
            passenger.lng = lng
            pass_key = passenger.put()
            newRide.passengers.append(pass_key)
            newRide.num_passengers = 1

        newRide.comment = self.request.get("comment")
        newRide.circle = self.request.get("circleType")
        ride_key = newRide.put()
        if not isDriver:
            passenger.ride = ride_key
            passenger.put()

        query = db.Query(Ride)
        query.filter("ToD > ", datetime.date.today())
        query.filter("circle = ",self.request.get("circle"))
        ride_list = query.fetch(limit=100)
        self.sendRideEmail(newRide)
        greeting = ''
        if user:
            greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>) Go to your <a href='/home'>Home Page</a>" %
                  (user.nickname(), users.create_logout_url("/")))
        message = 'Your ride has been created!'
        #doRender(self, 'map.html',{
        #    'ride_list': ride_list, 
        #    'greeting': greeting,
        #    'message': message,
        #    'mapkey' : MAP_APIKEY,
        #   })
        self.redirect("/map?circle="+str(self.request.get("circleType")))
        

    def sendRideEmail(self,ride):
      
        driverName = None
        passengerName = None
        subject = "New Ride "
        if ride.driver:
            if self.current_user.loginType == "google":
               to = self.current_user.email
               logging.debug(to)
            driverName = self.current_user.nickname()
        else:
            p = db.get(ride.passengers[0])
            logging.debug(p)
            #if self.current_user.loginType == "google":
               #to = p.email
            passengerName = self.current_user.nickname()
            
        sender = FROM_EMAIL_ADDR
        announceAddr = NOTIFY_EMAIL_ADDR
        if driverName:
            subject += "Announcement"
            body = """
A new ride is being offered.  %s is offering a ride from %s to %s on %s.
Please go to %s if you want to join this ride.

Thanks,

The Rideshare Team
""" % (driverName,ride.start_point_title,ride.destination_title,ride.ToD,rideshareWebsite)
        else:
            subject += "Request"
            body = """
A new ride request has been posted.  %s is looking for a ride from %s to %s on %s.
If you are able to take this person in your car, please go to %s
        
Thanks,

The Rideshare Team
""" % (passengerName,ride.start_point_title,ride.destination_title,ride.ToD,rideshareWebsite)

        if self.current_user.loginType == "facebook":
          logging.debug(self.current_user.access_token)
          graph = facebook.GraphAPI(self.current_user.access_token)
          graph.put_object("me", "feed", message=body)
          #pageGraph = facebook.GraphAPI("AAAECeZAfUaeoBAHYuYZC8NN9djZAlA6PZBpJnCWvZCxZBnDeEWQcdj3YuBZCWEJbPZA1E35QiCHqYmCxXsNkqT82tn67nMitdirfjxvZBAZBCfWzRKbCFZAHFZCH")
          #pageGraph.put_object("144494142268497","feed",message=body)

class AddPassengerHandler(BaseHandler): 
    """
    Handles addition of passengers
    """
    def get(self):
      """
      Called when adding a passenger to a ride
      
      Arguments:
      - 'self'
      
      Web Arguments:
      - user_name
      - ride_key
      """
      # The current user can add himself to the ride.  No need for this in the form.
      aquery = db.Query(College)
      mycollege= aquery.get()
      user_name = self.current_user.id
      
      ride_key = self.request.get('ride_key')
      contact = self.request.get('contact')
      address = self.request.get('address')
      lat = float(self.request.get('lat'))
      lng = float(self.request.get('lng'))
      ride = db.get(db.Key(ride_key))
      if ride == None: # Check if the ride was found
        temp = os.path.join(os.path.dirname(__file__), 'templates/error.html')
        outstr = template.render(temp, {'error_message': 'Error in ride matching'})
        self.response.out.write(outstr)
      # Check if the current user is the driver
      elif ride.max_passengers == ride.num_passengers:
        doRender(self, 'error.html', {'error_message': 'This ride is full'})
      # Check if the current user is already on the ride
      already = False
      for p in ride.passengers:
        if db.get(p).name== user_name:
          already = True
      if already:
        temp = os.path.join(os.path.dirname(__file__), 'templates/error.html')
        outstr = template.render(temp, {'error_message': 'You are already registered for this ride!'})
        self.response.out.write(outstr)
      # Check if the current user is already the driver for the ride
      elif user_name == ride.driver:
        doRender(self, 'error.html', {'error_message': 'You can\'t be a passenger for a ride which you a driving.'})
      else:
        passenger = Passenger()
        passenger.name = user_name
        passenger.fullname = FBUser.get_by_key_name(user_name).nickname()
        passenger.contact = contact
        passenger.location = address
        passenger.lat = lat
        passenger.lng = lng
        passenger.ride = db.Key(ride_key)
        pass_key = passenger.put()
        ride.num_passengers = ride.num_passengers + 1
        ride.passengers.append(pass_key)
        ride.put()

        if ride.num_passengers == ride.max_passengers:
          capacity_message = 'is now full.'
        else:
          num_left = ride.max_passengers - ride.num_passengers
          capacity_message = 'can hold ' + str(num_left) + ' more passengers.'
        query = db.Query(Ride)
        query.filter("ToD > ", datetime.date.today())
        ride_list = query.fetch(limit=100)
        user = self.current_user
        greeting = ''
        if user:
            greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>) Go to your <a href='/home'>Home Page</a>" %
                  (user.nickname(), users.create_logout_url("/")))
        message = 'You have been added to %s ride.' % (ride.driver)
        self.sendDriverEmail(ride)
        path = os.path.join(os.path.dirname(__file__), 'templates/map.html')
        self.response.out.write(template.render(path, {
            'ride_list': ride_list, 
            'greeting': greeting,
            'message': message,
            'mapkey':MAP_APIKEY, 
            'college':mycollege           
            }))

    def sendDriverEmail(self,ride):
        logging.debug(ride.driver)
        driver = FBUser.get_by_key_name(ride.driver)
        logging.debug(driver)
        if not ride.driver:
            return
        if driver.loginType == "google":
           to = driver
        else:
           logging.debug(ride.driver)
           to = FBUser.get_by_key_name(ride.driver)
           logging.debug(to)
        sender = FROM_EMAIL_ADDR
        subject = "New Passenger for your ride"
        p = db.get(ride.passengers[-1])
        user = FBUser.get_by_key_name(p.name)
        body = """
Dear %s,
We wanted to let you know that %s has been added to your ride
from %s to %s on %s.  If you need to contact %s you can do so at %s.

Thanks for being a driver!

Sincerely,

The Rideshare Team
""" % (to.nickname(), user.nickname(), ride.start_point_title, ride.destination_title,
       ride.ToD, user.nickname(), p.contact)

        if driver.loginType == "google":
          logging.debug(body)
          mail.send_mail(sender,to.email,subject,body)
        else:
          graph = facebook.GraphAPI(to.access_token)
          logging.debug(graph)
          graph.put_object("me", "feed", message=body)

class AddDriverHandler(BaseHandler):

    def get(self):
        ride_key = self.request.get("key")
        contact = self.request.get("contact")
        numpass = self.request.get("numpass")
        user = self.current_user
        
        ride = Ride.get(ride_key)
        ride.driver = user.id
        ride.drivername = FBUser.get_by_key_name(user.id).nickname()
        ride.contact = contact
        ride.max_passengers = int(numpass)
        ride.put()

        for p in ride.passengers:
            logger = logging.getLogger('MySite')
            logger.info(str(p))
            passenger = Passenger.get(p)
            if passenger.loginType =="google":
              self.sendRiderEmail(ride,passenger.email,"google")
            elif passenger.loginType=="facebook":
              self.sendRiderEmail(ride, passenger.name, "facebook")

        self.response.out.write("OK")

    def sendRiderEmail(self, ride, to,loginType):

        if loginType == "facebook":
           to = FBUser.get_by_key_name(to)
           user = self.current_user
           logging.debug(to)

        sender = FROM_EMAIL_ADDR
        subject = "Change in your ride"
        
        body = """
Dear %s,

We have good news about your request for a ride from %s to %s on %s.
%s has agreed to drive.  You can contact the driver at %s.

Have a safe trip!

Sincerely,

The Rideshare Team
""" % (to.nickname(),  ride.start_point_title, ride.destination_title, ride.ToD,
       user.nickname(), ride.contact)
        if loginType == "google": 
           logging.debug(body)
           mail.send_mail(sender,to,subject,body)
        else:
           graph = facebook.GraphAPI(to.access_token)
           graph.put_object("me", "feed", message=body)

class EditRideHandler(BaseHandler):
    def get(self):
        aquery = db.Query(College)
        mycollege= aquery.get()
        ride_key = self.request.get("key")
        ride = db.get(ride_key)
        username = self.current_user.id
        dayparts = ride.part_of_day.split()
        
        plist = []
        for p in ride.passengers:
            logging.debug(db.get(p).name)
            plist.append(db.get(p).name)
        
        doRender(self, 'edit.html', { 
                          'user': username,
                          'ride': ride,
                          'earlylate' : dayparts[0],
                          'mae' : dayparts[1],
                          'plist': plist,
                          'college':mycollege
                                         }
                 )

class ChangeRideHandler(BaseHandler):
    def post(self):
        aquery = db.Query(College)
        mycollege= aquery.get()
        user = self.current_user
        username = user.id
        ride = Ride.get(self.request.get("key"))

        contact = self.request.get("contact")
        comment = self.request.get("ridecomment")
        partofday = self.request.get("partofday")
        earlylate = self.request.get("earlylate")
        maxp = self.request.get("numpass")

        pofd = early_late_strings[earlylate] + " " + part_of_day_strings[partofday]

        ride.part_of_day = pofd
        ride.contact = contact
        ride.comment = comment
        ride.max_passengers = int(maxp)

        ride.put()
        self.redirect("/")
 
class UpdateCirclesHandler(BaseHandler):  #handles processing
    def post(self):
      user = FBUser.get_by_key_name(self.current_user.id)
      
      user.circles = self.request.str_params.getall("circle")
      user.put()
      self.redirect("/main")




class ChangeCirclesHandler(BaseHandler): #actual page for changing circles
    def get(self):
      aquery = db.Query(College)
      mycollege= aquery.get()
      allCircles = Circle.all()
      user = FBUser.get_by_key_name(self.current_user.id)
      doRender(self, "changecircles.html",{"circles":allCircles,"userCircles":user.circles,"college":mycollege})

class NewCircleHandler(BaseHandler): # actual page
    def get(self):
      aquery = db.Query(College)
      mycollege= aquery.get()  
      doRender(self, "newCircle.html",{"college":mycollege})


class AddCircleHandler(BaseHandler): #add Circle Processing
    def post(self):
      aquery = db.Query(College)
      mycollege= aquery.get()
      circleName = self.request.get("name")
      circleDesc = self.request.get("description")
      newCircle = Circle()
      newCircle.name = circleName
      newCircle.description = circleDesc
      newCircle.put()
      self.redirect("/")

class NewEventHandler(BaseHandler):
    def get(self):
      aquery = db.Query(College)
      mycollege= aquery.get()
      user = self.current_user
      newEvent = Event()
      newEvent.name = self.request.get("name")
      newEvent.lat = float(self.request.get("lat"))
      newEvent.lng = float(self.request.get("lng"))
      newEvent.address = self.request.get("address")
      newEvent.circle = self.request.get("circle")
      newEvent.time = self.request.get("time")
      newEvent.creator = self.current_user.id
      newEvent.ToD = datetime.date(int(self.request.get("year")),int(self.request.get("month")),int(self.request.get("day")))
      newEvent.put()

      query = db.Query(Ride)
      query.filter("ToD > ", datetime.date.today())
      query.filter("circle = ",self.request.get("circle"))
      ride_list = query.fetch(limit=100)
      greeting = ''
      if user:
            greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>) Go to your <a href='/home'>Home Page</a>" %
                  (user.nickname(), users.create_logout_url("/")))
      message = 'Your ride has been created!'
      path = os.path.join(os.path.dirname(__file__), 'templates/map.html')
      self.response.out.write(str(template.render(path, {
            'ride_list': ride_list, 
            'greeting': greeting,
            'message': message,
            'mapkey' : MAP_APIKEY,
            })))
class AddEventsHandler(BaseHandler):
    def get(self):
        aquery = db.Query(College)
        mycollege= aquery.get()
        circle = self.request.get("circle")
        doRender(self,"addevents.html",{"circle":circle,"college":mycollege})

class AddMultipleEventsHandler(BaseHandler):
    def post(self):
        logger = logging.getLogger('MySite')
        locations = self.request.str_params.getall("eventlocation")
        names = self.request.str_params.getall("eventname")
        dates = self.request.str_params.getall("eventdate")
        times = self.request.str_params.getall("eventtime")
        circle = self.request.get("circle")
        for i in range(len(locations)):
            if len(locations[i])>0:
                result = Geocoder.geocode(str(locations[i]))[0]
                logger.info(circle)
                if result:
                    newEvent = Event()
                    newEvent.creator = self.current_user.id
                    newEvent.name = names[i]
                    newEvent.lat = result.coordinates[0]
                    newEvent.lng = result.coordinates[1]
                    newEvent.address = locations[i]
                    newEvent.circle = circle
                    newEvent.time = times[i]
                    date = dates[i]
                    newEvent.ToD = datetime.date(int(date[6:]),int(date[0:2]),int(date[3:5]))
                    newEvent.put()
            
            
        self.redirect("/main")



class SubmitRatingHandler(BaseHandler):
    def post(self):
        aquery = db.Query(College)
        mycollege= aquery.get()  
        drivernum = self.request.get("driver")
        text = self.request.get("ratetext")
        ooFrating = self.request.get("ooFrating") # Out Of Five
        user= FBUser.get_by_key_name(drivernum)
        user.drivercomments.append(text)
        user.numrates = user.numrates + 1
    if user.rating== None:
        user.rating= float(ooFrating)
    else:
        user.rating= user.rating + float(ooFrating)
    user.put()
    doRender(self, "submit.html",{"college",mycollege})
    self.redirect("/home")

class HomeHandler(BaseHandler):
    """
    Displays personal homepage
    """
    def get(self):
      aquery = db.Query(College)
      mycollege= aquery.get()
      user = self.current_user
      username = user.id
      events = db.Query(Event)
      events.filter('creator =',self.current_user.id)
      event_list = events.fetch(limit=100)
      drive = db.Query(Ride)
      drive.filter('driver =', username)
      driverides = drive.fetch(limit=100)
      for ride in driverides:
        ride.passengerobjects = []
        ride.jsmonth = ride.ToD.month
        ride.jsyear = ride.ToD.year
        ride.jsday = ride.ToD.day 
        if ride.start_point_title == mycollege.name:
          ride.doOrPu = 0
        else:
          ride.doOrPu = 1
        for p in ride.passengers:
          ride.passengerobjects.append(db.get(p))
      passengers = db.Query(Passenger)
      passengers.filter('name =', username)
      passengerList = passengers.fetch(limit=100) # All passenger objects with 'my' name
      passengerrides = [] # Will contain all Rides the user is a passenger for
      for p in passengerList:
        passengerrides.append(p.ride)
      for ride in passengerrides:
        if ride.start_point_title == mycollege.name:
          ride.doOrPu = 0
        else:
          ride.doOrPu = 1
        ride.passengerobjects = [] # Will contain all Passenger objects for each Ride
        ride.jsmonth = ride.ToD.month
        ride.jsyear = ride.ToD.year
        ride.jsday = ride.ToD.day 
        for p in ride.passengers:
          ride.passengerobjects.append(db.get(p))
      doRender(self, 'home.html', { 
                          'college':mycollege,  
                          'user': user.nickname(),
                          'driverides': driverides, 
                          'logout':'/auth/logout',
                          'passengerrides': passengerrides,
                          'event_list':event_list })
    
class RideInfoHandler(BaseHandler):
    """
    Displays detailed information regarding a specific ride
    Holds a GMap detailing the trip
    """
    def get(self):
      aquery = db.Query(College)
      mycollege= aquery.get()
      username = self.current_user
      key = self.request.get('key')
      ride = db.get(key)
      if ride == None:
        doRender(self, 'error.html', {
                              'error_message': "No such ride exists.","college":mycollege})
      else:
        ride.passengerobjects = []
        ride.jsmonth = ride.ToD.month
        ride.jsyear = ride.ToD.year
        ride.jsday = ride.ToD.day
        if ride.start_point_title == mycollege.name:
          ride.doOrPu = 0
        else:
          ride.doOrPu = 1
        for p in ride.passengers:
          passenger = db.get(p)
          if (ride.start_point_lat == passenger.lat and ride.start_point_long == passenger.long) or (ride.destination_lat == passenger.lat and ride.destination_long == passenger.lng):
            passenger.samePlace = True;
          else:
            passenger.samePlace = False;
          ride.passengerobjects.append(passenger)           
        doRender(self, 'rideinfo.html', {
            'ride': ride,
            'mapkey':MAP_APIKEY,
            'college': mycollege
            })

class DeleteRideHandler(BaseHandler): #NEEDS WORK
    """
    Deletes a ride using a key
    """
    def get(self):
        key = self.request.get('key')
        ride = db.get(key)
        if ride == None:
            doRender(self, 'error.html', {
                              'error_message': "No such ride exists."})
        elif ride.num_passengers == 0:
            db.delete(ride)

        else:
            ride.driver = None
            ride.put()
            for p in ride.passengers:
              passenger = Passenger.get(p)
              passenger = FBUser.get_by_key_name(p.name)
              if passenger.loginType =="google":
                self.sendRiderEmail(ride,passenger.email,"google")
              elif passenger.loginType=="facebook":
                self.sendRiderEmail(ride, passenger.name, "facebook")

            
        user = self.current_user
        aquery = db.Query(College)
        mycollege= aquery.get()
        greeting = ''
        if user:
            greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>) Go to your <a href='/home'>Home Page</a>" %
                  (user.nickname(), users.create_logout_url("/")))
        message = 'Your ride has been deleted.'
        path = os.path.join(os.path.dirname(__file__), 'templates/map.html')
        self.response.out.write(template.render(path, {
            'greeting' : greeting,
            'message' : message,
            'mapkey':MAP_APIKEY, 
            'college': mycollege,
            'nick' : user.nickname()        
            }))

    def sendRiderEmail(self, ride, to,loginType):
        
        if loginType == "facebook":
          to = FBUser.get_by_key_name(to)
          logging.debug(to)
        sender = FROM_EMAIL_ADDR
        subject = "Change in your ride"
        
        body = """
Dear %s,

We wanted to let you know that there has been a change in status of your ride
from %s to %s on %s.  Unfortunately the driver is unable to drive anymore.
The ride will remain, but it will appear as a ride
that is in need of a driver.  When a new driver is found you will be notified
by email.


Sincerely,

The Rideshare Team
""" % (to.nickname(),  ride.start_point_title, ride.destination_title, ride.ToD)
        if loginType == "google":
          mail.send_mail(sender,to,subject,body)
        else:
 	  try:
             
             graph = facebook.GraphAPI(to.access_token)
             graph.put_object("me", "feed", message=body)

	  except:
	     logging.debug(graph.put_object("me", "feed", message=body))

class LoginPageHandler(BaseHandler):

  def get(self):
    aquery = db.Query(College)
    #global mycollege
    mycollege= aquery.get()
    
    user = self.current_user
    if user:
      self.redirect("/main")
    else:
      doRender(self, 'loginPage.html', {"name":mycollege.name,"college":mycollege})

class RateHandler(BaseHandler):
    
    def get(self):
      aquery = db.Query(College)
      mycollege= aquery.get()  
      drivernum = self.request.get('dkey')
      user = FBUser.get_by_key_name(drivernum)
      doRender(self, 'ratedriver.html', {
            'driver': user.nickname(),
            'drivernum':drivernum,
            'college':mycollege
            })
      

class RemovePassengerHandler(BaseHandler):
    """
    Removes a passenger using a key and the current user
    """
    def get(self):
      rkey = self.request.get('rkey')
      ride = db.get(rkey)
      pkey = self.request.get('pkey')
      passenger = db.get(pkey)
      #self.response.out.write('Would remove %s from %s ride' % (passenger.name, ride.driver))
      if ride == None:
        doRender(self, 'error.html', {
                              'error_message': "No such ride exists."})
      elif passenger == None:
        doRender(self, 'error.html', {
                              'error_message': "No such passenger exists."})
      else:
        name = passenger.name
        ride.passengers.remove(passenger.key())
        passenger.delete()
        ride.num_passengers -= 1
        ride.put()
        query = db.Query(Ride)
        query.filter("ToD > ", datetime.date.today())
        ride_list = query.fetch(limit=100)
        user = self.current_user
        aquery = db.Query(College)
        mycollege= aquery.get()
        greeting = ''
        if user:
            greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>) Go to your <a href='/home'>Home Page</a>" %
                  (user.nickname(), users.create_logout_url("/")))
        message = '%s has been removed from %s\'s ride.' % (name, ride.driver)
        path = os.path.join(os.path.dirname(__file__), 'templates/map.html')
        self.response.out.write(str(template.render(path, {
            'ride_list': ride_list, 
            'greeting' : greeting,
            'college': mycollege,
            'address': mycollege.address,
            'nick' : user.nickname(),
            'logout':'/auth/logout',
            'mapkey':MAP_APIKEY,
            })))

class DriverRatingHandler(BaseHandler):

    def get(self):
      drivernum = self.request.get('drivernum')
      user = FBUser.get_by_key_name(drivernum)
      ratingslist= user.drivercomments
      name = user.nickname()
      if user.rating != None:
          rating = user.rating/user.numrates
      else:
          rating= 0.00
      numrates = user.numrates
      
      doRender(self, 'driverrating.html', {
          'ratingslist': ratingslist,
          'name': name,
          'rating':str(rating)[0:3],
          'numrates':numrates })




class SchoolErrorHandler(BaseHandler):
    
    def get(self):
      aquery = db.Query(College)
      mycollege= aquery.get() 
      doRender(self, 'schoolerror.html',{"college":mycollege})

class RideSuccessHandler(BaseHandler):
    
    def get(self):
       aquery = db.Query(College)
       mycollege= aquery.get() 
       noDriver = 0
       noPass = 0
       goodRide = 0
       myquery = db.Query(Ride)
       rides = myquery.fetch(limit=1000000)
       for ride in rides:
           logging.debug(ride.driver)
           if ride.driver == None:
               noDriver += 1
           else:
               if ride.num_passengers >0:
                   goodRide += 1
               else:
                   noPass += 1
       doRender(self, 'ridesuccess.html', {
                'noDriver': noDriver,
                'noPass': noPass,
                'goodRide': goodRide,
                'totalRides':len(rides),
                'college':mycollege})   

class ConnectPageHandler(BaseHandler):

    def get(self):
        user = self.current_user
        userID = user.id
        doRender(self, 'connectride.html',{
            'drivernum': userID})

class DatabaseHandler(BaseHandler):
    def get(self):
        ID = self.request.get('ID', None)
        
        if ID is None:
            # First request, just get the first name out of the datastore.
            ride = db.Query(Ride).get()
            ID = ride.ID

        q = db.Query(Ride)
        rides = q.fetch(limit=2)
        current_ride = rides[0]
        if len(rides) == 2:
            next_ride = rides[1].ID
            next_url = '/update?ID=%s' % urllib.quote(next_ride)
        else:
            next_ride = 'FINISHED'
            next_url = '/'  # Finished processing, go back to main page.
        # In this example, the default values of 0 for num_votes and avg_rating are
        # acceptable, so we don't need to do anything other than call put().
        if not isinstance(current_ride.driver,str):
           current_ride.put()

        context = {
            'current_name': ID,
            'next_name': next_ride,
            'next_url': next_url,
        }
        self.response.out.write(template.render('update.html', context))


class IncorrectHandler(webapp.RequestHandler):
    """
    Returns an error for URLs not defined
    """
    def get(self):
      doRender(self, 'error.html', {
                            'error_message': "Page does not exist."})

class MovePassengerHandler(BaseHandler):
    def post(self):
        user= self.current_user
        keys = self.request.get("keys")
        keyList = keys.split("|")
        pRide= Ride.get(keyList[0])
        dRide= Ride.get(keyList[1])
        logging.debug(dRide)
        for passenger in pRide.passengers:
            if dRide.passengers:
                dRide.passengers.append(passenger)
            else:
                dRide.passengers=[passenger]
        dRide.num_passengers = dRide.num_passengers +len(pRide.passengers)
        dRide.put()
        db.delete(keyList[0])

        greeting = ''
        if user:
            greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>) Go to your <a href='/home'>Home Page</a>" %
                        (user.nickname(), users.create_logout_url("/")))
        message = 'You have added passengers to your ride.'
        path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
        self.response.out.write(template.render(path, {
            'greeting' : greeting,
            'message' : message,
            'mapkey':MAP_APIKEY,
            }))

class SignOutHandler(BaseHandler):
    def get(self):
      aquery = db.Query(College)
      mycollege= aquery.get()
      doRender(self, 'logout.html', { 'logout_message': "Thanks for using the "+ mycollege.name + " Rideshare Website!","college":mycollege})

def doRender(handler, name='map.html', value={}):
    temp = os.path.join(os.path.dirname(__file__), 'templates/' + name)
    outstr = template.render(temp, value)
    handler.response.out.write(str(outstr))

def geocode(address):
 # This function queries the Google Maps API geocoder with an
 # address. It gets back a csv file, which it then parses and
 # returns a string with the longitude and latitude of the address.

 # This isn't an actual maps key, you'll have to get one yourself.
 # Sign up for one here: http://code.google.com/apis/maps/signup.html
#  mapsKey = 'ABQIAAAAn9H2MPjtzJCGP4OYVLJuOxQbtjENHIgppMgd3dAaKy16g5o_8xTNamzlZZNZ42SPIkttrL_Smwh7RQ'

  mapsUrl = 'http://maps.google.com/maps/geo?q='
     
 # This joins the parts of the URL together into one string.
  url = ''.join([mapsUrl,urllib.quote(address),'&output=csv&key=',MAP_APIKEY])
    
 # This retrieves the URL from Google, parses out the longitude and latitude,
 # and then returns them as a string.
  coordinates = urllib.urlopen(url).read().split(',')
  #coorText = '%s,%s' % (coordinates[3],coordinates[2])
  return (float(coordinates[3]),float(coordinates[2]))

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('Hello, WebApp World!')


app = webapp2.WSGIApplication([
                              ('/', LoginPageHandler),
                              ('/map', MapHandler),
                              ('/main',MainHandler),
                              ('/getrides', RideQueryHandler ),
                              ("/newride.*", NewRideHandler),
                              ("/addpass", AddPassengerHandler),
                              ("/adddriver",AddDriverHandler),                                          
                              ('/home', HomeHandler),
                              ('/rideinfo', RideInfoHandler),
                              ('/deleteride', DeleteRideHandler),
                              ('/editride', EditRideHandler),
                              ('/applyedits', ChangeRideHandler),
                              ('/removepassenger', RemovePassengerHandler),
                              ('/auth/login', LoginHandler),
                              ('/auth/logout',LogoutHandler),
                                      ('/signout', SignOutHandler),                
                                      ('/ratedriver', RateHandler),
                                      ('/submittext', SubmitRatingHandler),
                              ('/driverrating',DriverRatingHandler),
                                      ('/school',SchoolErrorHandler),
                              ('/ridesuccess',RideSuccessHandler),
                              ('/updateCircles',UpdateCirclesHandler),
                              ('/changecircles',ChangeCirclesHandler),
                              ('/addCircle', AddCircleHandler),
                              ('/newCircle',NewCircleHandler),
                              ('/newevent',NewEventHandler),
                              ('/getevents',EventQueryHandler),
                              ('/neweventride', NewEventRideHandler),
                              ('/addevents',AddEventsHandler),
                              ('/addmultipleevents',AddMultipleEventsHandler),
                              ('/movepass', MovePassengerHandler),
                              ('/connectride',ConnectPageHandler),
                              ('/databasefix', DatabaseHandler),
                              ('/.*', IncorrectHandler),
                              ],
                              debug=True)

# def main():
#     global MAP_APIKEY, FROM_EMAIL_ADDR, NOTIFY_EMAIL_ADDR

#     logging.getLogger().setLevel(logging.DEBUG)
#     # prepopulate the database
#     query = db.Query(Ride)
    
    # application = webapp.WSGIApplication([
    #                               ('/', LoginPageHandler),
    #                               ('/map', MapHandler),
    #                               ('/main',MainHandler),
    #                               ('/getrides', RideQueryHandler ),
    #                               ("/newride.*", NewRideHandler),
    #                               ("/addpass", AddPassengerHandler),
    #                               ("/adddriver",AddDriverHandler),                                          
    #                               ('/home', HomeHandler),
    #                               ('/rideinfo', RideInfoHandler),
    #                               ('/deleteride', DeleteRideHandler),
    #                               ('/editride', EditRideHandler),
    #                               ('/applyedits', ChangeRideHandler),
    #                               ('/removepassenger', RemovePassengerHandler),
    #                               ('/auth/login', LoginHandler),
    #                               ('/auth/logout',LogoutHandler),
				#                           ('/signout', SignOutHandler),                
				#                           ('/ratedriver', RateHandler),
				#                           ('/submittext', SubmitRatingHandler),
    #                               ('/driverrating',DriverRatingHandler),
				#                           ('/school',SchoolErrorHandler),
    #                               ('/ridesuccess',RideSuccessHandler),
    #                               ('/updateCircles',UpdateCirclesHandler),
    #                               ('/changecircles',ChangeCirclesHandler),
    #                               ('/addCircle', AddCircleHandler),
    #                               ('/newCircle',NewCircleHandler),
    #                               ('/newevent',NewEventHandler),
    #                               ('/getevents',EventQueryHandler),
    #                               ('/neweventride', NewEventRideHandler),
    #                               ('/addevents',AddEventsHandler),
    #                               ('/addmultipleevents',AddMultipleEventsHandler),
    #                               ('/movepass', MovePassengerHandler),
    #                               ('/connectride',ConnectPageHandler),
    #                               ('/databasefix', DatabaseHandler),
    #                               ('/.*', IncorrectHandler),
    #                               ],
    #                               debug=True)
#     wsgiref.handlers.CGIHandler().run(application)


# if __name__ == '__main__':
#   main()

# This is actually the development one.
# lutherrideshare.appspot key: ABQIAAAAg9WbCE_zwMIRW7jDFE_3ixS0LiYWImofzW4gd3oCqtkHKt0IaBT-STdq-gdH-mW2_ejMPXqxnfJjgw

# This has the app id of ridesharebeta   and is also on ridesharebeta.appspot.com
# rideshare.luther.edu key:  ABQIAAAAg9WbCE_zwMIRW7jDFE_3ixQ2JlMNfqnGb2qqWZtmZLchh1TSjRS0zuchuhlR8g4tlMGrjg34sNmyjQ
