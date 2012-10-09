import json
import wowhead
import random
import string

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.template import Template, Context
from django.template.loader import get_template
from django.core.paginator import Paginator, EmptyPage

from worldofloot.settings import DEBUG
from worldofloot.main.models import UserProfile
from worldofloot.main.models import Pin
from worldofloot.main.models import Item
from worldofloot.main.models import Image

ITEM_BLOCK_SIZE = 5

def global_render(request, path, args):
  first_visit = False
  if not request.session.get('visited', False):
    first_visit = True
  args['first_visit'] = first_visit

  args['debug'] = DEBUG
  return render(request, path, args)

def index(request):
  return popular(request)

def user(request, username):
  items, comments_by_item = get_user_loot_items(request, username, '0')

  return global_render(request, 'main/users.html', {
    'items': items,
    'tab': 'user_loot/' + username,
    'comments_by_item': comments_by_item,
  })

def about(request):
  return global_render(request, 'main/about.html', {})

def recent(request):
  if 'anon_key' not in request.session:
    # we use our own session key because was having
    # problems accessing session.session_key before it was set.
    request.session['anon_key'] = random_string(20)

  template_items, comments_by_item = get_recent_items(request)

  return global_render(request, 'main/myloot.html', {
    'items': template_items,
    'tab': 'recent',
    'comments_by_item': comments_by_item,
  })

def get_recent_items(request, str_page='0'):
  page = int(str_page)
  try:
    pins = Paginator(Pin.objects.order_by('-created'), ITEM_BLOCK_SIZE).page(page+1)
  except EmptyPage:
    return [], []

  items = []
  comments_by_item = {}
  for pin in pins:
    comments_by_item.setdefault(pin.item, [])
    if pin.comment and len(pin.comment) > 0:
      comment_user = pin.user.username if pin.user else 'anonymous'
      comments_by_item[pin.item].append({'user': comment_user, 'comment': pin.comment})
    items.append(pin.item)
  template_items = set_images_for_items(uniq(items))

  return template_items, comments_by_item

def popular(request):
  if 'anon_key' not in request.session:
    # we use our own session key because was having
    # problems accessing session.session_key before it was set.
    request.session['anon_key'] = random_string(20)

  template_items, comments_by_item = get_popular_items(request)
  return global_render(request, 'main/myloot.html', {
    'items': template_items,
    'tab': 'popular',
    'comments_by_item': comments_by_item,
  })

def get_popular_items(request, str_page='0'):
  page = int(str_page)
  try:
    pins = Paginator(Pin.objects.order_by('-item__popularity', '-created'), ITEM_BLOCK_SIZE).page(page+1)
  except EmptyPage:
    return [], []

  items = []
  comments_by_item = {}
  for pin in pins:
    comments_by_item.setdefault(pin.item, [])
    if pin.comment and len(pin.comment) > 0:
      comment_user = pin.user.username if pin.user else 'anonymous'
      comments_by_item[pin.item].append({'user': comment_user, 'comment': pin.comment})
    items.append(pin.item)
  template_items = set_images_for_items(uniq(items))

  return template_items, comments_by_item


def popular_json(request, page):
  return api_response(request, get_popular_items, page)

def recent_json(request, page):
  return api_response(request, get_recent_items, page)

def my_loot_json(request, page):
  return api_response(request, get_my_loot_items, page)

def user_loot_json(request, username, page):
  # special case
  items, comments_by_item = get_user_loot_items(request, username, page)
  pin_html = ''
  for item in items:
    context = Context({
      'item': item,
      'comments_by_item': comments_by_item,
      'hide_image': 'False',
    })
    pin_html += get_template('main/pin.html').render(context)
  response = { 'success': True, 'pin_html': pin_html.replace('\n', ''), }
  return HttpResponse(json.dumps(response), mimetype="application/json")

def api_response(request, fn, page):
  items, comments_by_item = fn(request, page)
  pin_html = ''
  for item in items:
    context = Context({
      'item': item,
      'comments_by_item': comments_by_item,
      'hide_image': 'False',
    })
    pin_html += get_template('main/pin.html').render(context)
  response = { 'success': True, 'pin_html': pin_html.replace('\n', ''), }
  return HttpResponse(json.dumps(response), mimetype="application/json")

def my_loot(request):
  # Stop showing the enticing top banner
  request.session['visited'] = True
  # get pins
  if 'anon_key' not in request.session:
    # we use our own session key because was having
    # problems accessing session.session_key before it was set.
    request.session['anon_key'] = random_string(20)

  items, comments_by_item = get_my_loot_items(request)

  return global_render(request, 'main/myloot.html', {
    'items': items,
    'tab': 'my_loot',
    'comments_by_item': comments_by_item,
  })

def get_my_loot_items(request, str_page='0'):
  if request.user.is_authenticated():
    pins = Pin.objects.filter(user=request.user)
  else:
    pins = Pin.objects.filter(session=request.session['anon_key'], user__isnull=True)
  return get_generic_user_page_items(request, str_page, pins)

def get_user_loot_items(request, username, str_page='0'):
  user_obj = get_object_or_404(User, username=username)
  pins = Pin.objects.filter(user=user_obj)
  return get_generic_user_page_items(request, str_page, pins)

def get_generic_user_page_items(request, str_page, pins):
  # This "get_X_items" is special, it needs the request
  page = int(str_page)
  try:
    pins = Paginator(pins, ITEM_BLOCK_SIZE).page(page+1)
  except EmptyPage:
    return [], []


  items = []
  comments_by_item = {}
  for pin in pins:
    item = pin.item

    # Add comment
    comments_by_item.setdefault(item, [])
    if pin.comment and len(pin.comment) > 0:
      comment_user = pin.user.username if pin.user else 'anonymous'
      comments_by_item[pin.item].append({'user': comment_user, 'comment': pin.comment})

    # Choose images
    images = item.image_set.order_by('priority')
    if len(images) > 0:
      item.image = images[0]
    items.append(item)

  items = uniq(items)
  return items, comments_by_item


def get_item_info(request, item_type, item_id):
  try:
    id = int(item_id)
  except:
    return HttpResponse(status=500)

  try:
    item = Item.objects.get(item_id=id, item_type=item_type)
    print 'Item #', id, 'already exists in database'
  except Item.DoesNotExist:
    print 'Grabbing info for item #', id
    item = wowhead.scrape_item(id, item_type)

  response = {'success': True, 'images': [], 'name': item.name}
  for image in Image.objects.filter(item=item).order_by('priority'):
    response['images'].append(image.path)

  # TODO handle no images found
  return HttpResponse(json.dumps(response), mimetype="application/json")


def add_item(request, item_type, item_id, verb):
  if 'anon_key' not in request.session:
    # we use our own session key because was having
    # problems accessing session.session_key before it was set.
    request.session['anon_key'] = random_string(20)
  if verb not in ['want', 'have']:
    return HttpResponse('bad verb', status=500)

  try:
    id = int(item_id)
  except:
    return HttpResponse('bad id', status=500)

  try:
    item = Item.objects.get(item_id=id, item_type=item_type)
  except Item.DoesNotExist:
    print 'Serving 500 because we got an add request for an item not yet scraped'
    return HttpResponse(status=500)

  already_have = False
  increment_item_verb = False
  if request.user.is_authenticated():
    # logged in
    try:
      pin = Pin.objects.get(item=item, user=request.user)
      # check to make sure they didn't switch verb
      if pin.verb == verb:
        already_have = True
      else:
        # keep old wants and haves
        increment_item_verb = True
        pin.verb = verb
        pin.save()
    except Pin.DoesNotExist:
      pin = Pin(item=item, user=request.user, \
          comment=request.POST.get('comment', None).strip()[:199])
      pin.save()
      increment_item_verb = True
  else:
    # TODO session expiration
    try:
      pin = Pin.objects.get(item=item, session=request.session['anon_key'])
      # check to make sure they didn't switch verb
      if pin.verb == verb:
        already_have = True
      else:
        # keep old wants and haves
        increment_item_verb = True
        pin.verb = verb
        pin.save()
    except Pin.DoesNotExist:
      pin = Pin(item=item, session=request.session['anon_key'], \
          comment=request.POST.get('comment', None).strip()[:199])
      pin.save()
      increment_item_verb = True

  if increment_item_verb:
    if verb == 'want':
      item.increment_wants()
    elif verb == 'have':
      item.increment_haves()
    item.save()

  # build json response

  # build pin render context
  item = set_image_for_item(item)
  comments_by_item = {}
  comments_by_item.setdefault(item, [])
  if pin.comment and len(pin.comment) > 0:
    comment_user = pin.user.username if pin.user else 'anonymous'
    comments_by_item[item].append({'user': comment_user, 'comment': pin.comment})
  # render pin
  pin_html = get_template('main/pin.html').render( \
      Context({
        'item': item,
        'comments_by_item': comments_by_item,
        'hide_image': 'False',
      }))
  response = {'success': True, 'already_have': already_have, \
      'pin_html': pin_html,
      }
  return HttpResponse(json.dumps(response), mimetype="application/json")

def remove_item(request, item_type, item_id):
  # doing this by item_id for now...maybe in the future take a pin id?
  try:
    id = int(item_id)
  except:
    return HttpResponse('bad id', status=500)

  item = Item.objects.get(item_id=item_id, item_type=item_type)
  if request.user.is_authenticated():
    Pin.objects.filter(user=request.user, item=item).delete()
  else:
    Pin.objects.filter(session=request.session['anon_key'], item=item).delete()

  return HttpResponse(status=200)

def turn_off_welcome_banner(request):
  request.session['visited'] = True
  return HttpResponse(status=200)

# TODO move this to its own app
# csrf reference, see https://docs.djangoproject.com/en/dev/ref/contrib/csrf/
# auth reference, see https://docs.djangoproject.com/en/dev/topics/auth/
def login_or_create(request):
  if 'anon_key' not in request.session:
    # we use our own session key because was having
    # problems accessing session.session_key before it was set.
    request.session['anon_key'] = random_string(20)

  # validation
  if 'username' not in request.POST or 'password' not in request.POST:
    return HttpResponse('bad request', status=500)
  username = request.POST['username']
  password = request.POST['password']
  if not request.POST.get('remember_me', None):
    request.session.set_expiry(0)

  # Add user if applicable, then login
  user = authenticate(username=username, password=password)
  if user is None:
    # New user - create and transfer the pinz to them
    User.objects.create_user(username, '', password)
    user = authenticate(username=username, password=password)
    convert_session_to_user(request, user)
    print 'User', username, 'created'
  return login_user(request, user)

def login_user(request, user):
    if user.is_active:
      login(request, user)
      print 'User', user.username, 'logged in'
      response = {'success': True}
      return HttpResponse(json.dumps(response), mimetype="application/json")
    else:
      response = {'success': False, 'reason': 'User deactivated'}
      return HttpResponse(json.dumps(response), mimetype="application/json")

def convert_session_to_user(request, user):
  pins = Pin.objects.filter(session=request.session['anon_key'], user__isnull=True)
  for pin in pins:
    pin.user = user
    pin.save()

def logout_user(request):
  logout(request)
  return HttpResponse("You've been logged out.")

def random_string(n):
  return ''.join(random.choice(string.ascii_letters + string.digits + string.punctuation) for x in range(n))

def set_images_for_items(items):
  ret = []
  for item in items:
    item = set_image_for_item(item)
    ret.append(item)
  return ret

def set_image_for_item(item):
  images = item.image_set.order_by('priority')
  if len(images) > 0:
    item.image = images[0]
  return item

# dedupes a list but keeps order
# http://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-python-whilst-preserving-order
def uniq(seq):
  seen = set()
  seen_add = seen.add
  ret = [x for x in seq if x.get_uid() not in seen and not seen_add(x.get_uid())]
  return ret
