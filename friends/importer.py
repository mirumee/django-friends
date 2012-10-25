from django.conf import settings
from django.utils import simplejson as json

import gdata.contacts.service
import vobject

import yahoo.oauth, yahoo.yql, yahoo.application

from friends.models import Contact


def import_vcards(stream, user):
    """
    Imports the given vcard stream into the contacts of the given user.
    
    Returns a tuple of (number imported, total number of cards).
    """
    
    total = 0
    imported = 0
    for card in vobject.readComponents(stream):
        total += 1
        try:
            name = card.fn.value
            email = card.email.value
            try:
                Contact.objects.get(user=user, email=email)
            except Contact.DoesNotExist:
                Contact(user=user, name=name, email=email).save()
                imported += 1
        except AttributeError:
            pass # missing value so don't add anything
    return imported, total

def import_yahoo(access_token, user):
    """
    Uses the given Access token to retrieve a Yahoo Address Book and
    import the entries with an email address into the contacts of the
    given user.

    Returns a tuple of (number imported, total number of entries).
    """

    oauthapp = yahoo.application.OAuthApplication(settings.YAHOO_CONSUMER_KEY, settings.YAHOO_CONSUMER_SECRET, settings.YAHOO_APPLICATION_ID, None)
    oauthapp.token = yahoo.oauth.AccessToken.from_string(access_token)
    address_book = oauthapp.getContacts()

    total = 0
    imported = 0

    for contact in address_book["contacts"]['contact']:
        total += 1
        email = contact['fields'][0]['value']
        try:
            first_name = contact['fields'][1]['givenName']
        except (KeyError, IndexError):
            first_name = None
        try:
            last_name = contact['fields'][1]['familyName']
        except (KeyError, IndexError):
            last_name = None
        if first_name and last_name:
            name = first_name + " " + last_name
        elif first_name:
            name = first_name
        elif last_name:
            name = last_name
        else:
            name = None
        try:
            Contact.objects.get(user=user, email=email)
        except Contact.DoesNotExist:
            Contact(user=user, name=name, email=email).save()
            imported += 1

    return imported, total

def import_google(authsub_token, user):
    """
    Uses the given AuthSub token to retrieve Google Contacts and
    import the entries with an email address into the contacts of the
    given user.
    
    Returns a tuple of (number imported, total number of entries).
    """
    
    contacts_service = gdata.contacts.service.ContactsService()
    contacts_service.SetAuthSubToken(authsub_token)
    contacts_service.UpgradeToSessionToken()
    entries = []
    feed = contacts_service.GetContactsFeed()
    entries.extend(feed.entry)
    next_link = feed.GetNextLink()
    while next_link:
        feed = contacts_service.GetContactsFeed(uri=next_link.href)
        entries.extend(feed.entry)
        next_link = feed.GetNextLink()
    total = 0
    imported = 0
    for entry in entries:
        name = entry.title.text
        for e in entry.email:
            email = e.address
            total += 1
            try:
                Contact.objects.get(user=user, email=email)
            except Contact.DoesNotExist:
                Contact(user=user, name=name, email=email).save()
                imported += 1
    return imported, total
