#!/usr/bin/python

import httplib, json
import mysql.connector
import requests
import os

#square access token
ACCESS_TOKEN = 'MY_ACCESS_TOKEN'
#opencart database server
DATABASE_SERVER = 'MYSQL_SERVER_NAME'
#opencart database username/password
DATABASE_USER = 'MYSQL_USERNAME'
DATABASE_USER_PASSWORD = 'MYSQL_PASSWORD'
#opencart database name
DATABASE_NAME = 'OPENCART_DATABASE_NAME'

#root location of folder that contains the images referred to as relative paths
#in the database, usually, websitelocation/image
IMAGE_FILE_LOCATION = '/mywebsite/image'

def create_item(item):
  """
  Create product in Square
  Uploads image
  
  returns inventory data for each variant as a list of dict objects
  
  If inventory is updated immediately after creating the product, we get a
  product not found error
  
  """
  print 'Creating item'
  request_body = json.dumps(item)
  
  connection.request('POST', '/v1/me/items', request_body, request_headers)
  response = connection.getresponse()
  response_body = json.loads(response.read())

  if response.status == 200:
    print 'Successfully created item:'

    # Pretty-print the returned Item object
    print json.dumps(response_body, sort_keys=True, indent=2, separators=(',', ': '))
    image_id = response_body['id']
    image_url = item["image"]
    upload_image(image_id, image_url)
    
    inventory_list = []    
    
    for v in response_body['variations']:    
        variant_id = v['id']
            
        for ov in item['variations']:
            if ov['sku'] == v['sku']:
                quantity = ov['quantity']

        inventory = {'variant_id':variant_id, 'quantity':quantity }
        inventory_list.append(inventory)
    
    return inventory_list
    
  else:
    print response.status
    print response.read()
    print 'Item creation failed'
    return None

def upload_image(item_id, image_path):
    """
    Upload an image for a Square product
    """
    session = requests.Session()
    session.headers['Authorization'] = 'Bearer ' + ACCESS_TOKEN

    image_name =  image_path.split("/")[8]
    image_url = 'https://connect.squareup.com/v1/me/items/{0}/image'.format(item_id)
    files = {'image_data' : (image_name, open(image_path,'rb'),'image/jpeg')}

    r = session.post(image_url, files=files)
    print r.text  
 
def get_categories():
    """
    retrieves a list of square categories
    returns the square response as a dict
    """
    connection.request('GET', '/v1/me/categories', headers= request_headers)
    response = connection.getresponse()
    response_body = json.loads(response.read())
    return response_body
    

def delete_item(item_id):
  """
  Deletes a Square product
  """
  print 'Deleting item ' + item_id
  connection.request('DELETE', '/v1/me/items/' + item_id, '', request_headers)
  response = connection.getresponse()
  response_body = json.loads(response.read())
  if response.status == 200:
    print 'Successfully deleted item'
    return response_body
  else:
    print 'Item deletion failed'
    return None


def list_items():
    """
    returns a list of Square products as a list
    """
    connection.request('GET', '/v1/me/items', headers = request_headers)

    response = connection.getresponse()
    response_body = json.loads(response.read())
    return response_body

def update_inventory(variant_id, quantity):
    """
    Update inventory data for a variant
    """
    
    data = {'quantity_delta':quantity,
            'adjustment_type':'MANUAL_ADJUST'
    }
    request_body = json.dumps(data)
    connection.request('POST', '/v1/me/inventory/' + variant_id,request_body, request_headers)
    response = connection.getresponse()
    response_body = json.loads(response.read())
    
    print response_body
    
def process_variation(variation_name, price, sku, product_id, quantity):
    """
    returns a dict for a specific variant
    
    quantity is not actually a square support property. Square will ignore this.
    This field is used to record the quantity for the variant so inventory 
    can be updated
    """    
    variation_processed = {'name' :  variation_name,
                           'pricing_type': 'FIXED_PRICING',
                           'price_money' : {
                               'currency_code':'AUD',
                               'amount':float(price) * 100
                           },
                           'sku': sku,
                           'track_inventory': True,
                           'user_data':str(product_id),
                           'inventory_alert_threshold':2,
                           'inventory_alert_type':'LOW_QUANTITY',
                           'quantity': quantity
                             }   
    return variation_processed
    
def get_opencart_products():
    """
    Queries the opencart mysql database for product and variations sorted by
    product_id
    
    Builds up product in Square's Product and variations structure. By iterating
    the ordered result set and building up the variation list and product dict
    
    image is not a valid square property, square will ignore this. This is
    used to update the images after the product has been created.
    
    Returns list of products as dict objects
    
    """
    categories = get_categories()    
    cached_categories = {}   
    for cat in categories:
        cached_categories[cat['name']] = cat['id']
    
    
    cnx = mysql.connector.connect(user = DATABASE_USER, 
                                  password = DATABASE_USER_PASSWORD, 
                                  database=DATABASE_NAME, 
                                  host=DATABASE_SERVER)
    cursor = cnx.cursor()
    query = ("""select d.name productName
, c.name categoryName
, p.price
, case 
    when colour.valueName is not null then concat(p.model,left(colour.valueName,1)) 
    else p.model
  end SKU
, case 
    when colour.valueName is null then size.valueName
    when size.valueName is null then colour.valuename
    else concat(colour.valueName, ' ', size.valueName) 
end Variation
, d.product_id
, concat('{0}', p.image) image_url
,  COALESCE(size.quantity, colour.quantity,p.quantity) quantity
from oc_product_description d
join 
(
    select product_id, min(category_id) category_id
    from oc_product_to_category
    group by product_id
) pc
on pc.product_id = d.product_id
join oc_category_description c on c.category_id = pc.category_id
join oc_product p on p.product_id = d.product_id
left join
(
select po.product_id, o.name optionName, v.name valueName, po.quantity
from oc_product_option_value po
join oc_option_description o on po.option_id = o.option_id
join oc_option_value_description v on po.option_value_id = v.option_value_id
where o.name = 'colour'
and po.quantity > 0
) colour 
ON colour.product_id = d.product_id
left join 
(
select po.product_id, o.name optionName, v.name valueName, po.quantity
from oc_product_option_value po
join oc_option_description o on po.option_id = o.option_id
join oc_option_value_description v on po.option_value_id = v.option_value_id
where o.name = 'ring size'
and po.quantity > 0
) size
on size.product_id = d.product_id

where d.language_id = 2
and c.language_id = 2
""".format(IMAGE_FILE_LOCATION))

    cursor.execute(query)

    products = []
    variations = []
    product = {}
    previous_product_id = 0
    is_first_iteration = True
    for (productName, catagory_name, price, sku, variation, product_id, image_url, quantity) in cursor:
        #new product, finish processing completed product    
        if previous_product_id != product_id:        

            if not is_first_iteration:            
                product['variations'] = variations
                products.append(product)
            
            #Reset product
            variations = []
            category_id = cached_categories[catagory_name]
            
            product = {'name': productName,
                       'category_id': category_id,
                       'available_for_pickup': True,
                       'available_online':True,
                       'image':image_url}
            
            if variation == None: 
                variation_name = productName 
            else:
                variation_name = variation                
                
            variation_processed = process_variation(variation_name, 
                                                    price, 
                                                    sku, 
                                                    product_id, 
                                                    quantity)            
        
            
            variations.append(variation_processed)
            
        #still same product continue appending variations
        else:
            if variation == None: 
                variation_name = productName 
            else:
                variation_name = variation      
                
            variation_processed = process_variation(variation_name, 
                                                    price, 
                                                    sku, 
                                                    product_id, 
                                                    quantity)         
            
            variations.append(variation_processed)             
        
        is_first_iteration = False
        previous_product_id = product_id

    #process last product    
    product['variations'] = variations
    products.append(product) 
    
    cursor.close()
    cnx.close()

    return products

   

def get_fees():
    """
    Retrieves a list of fees setup such as tax
    returns a list of dict objects
    """
    connection.request('GET', 
                        '/v1/me/fees',
                        headers= request_headers)
    response = connection.getresponse()
    response_body = json.loads(response.read())
    return response_body
    
def apply_fee(item_id, fee_id):
    """
    Enable a specific fee for a specific product
    @param item_id square item_id
    @param fee_id square fee_id
    
    returns a list of dict objects
    """
    connection.request('PUT', 
                        '/v1/me/items/{0}/fees/{1}'.format(item_id, fee_id),
                        headers= request_headers)
    response = connection.getresponse()
    response_body = json.loads(response.read())
    return response_body

if __name__ == '__main__':
  """
  Retrieves product list from opencart DB and uploads to Square
  Checks that all images exist, if not an exception is raised
  Migrates variants, inventory, master image and categories, enables tax fee
  for all products
  
  Limitations:
  Assumes all opencart catagories already exists in square
  Where a product has multiple options, inventory is not recorded correctly
  since opencart does not record this
  Assumes Tax fee is the first fee in the list
   
  """

  connection = httplib.HTTPSConnection('connect.squareup.com')

  request_headers = {'Authorization': 'Bearer ' + ACCESS_TOKEN,
                   'Accept': 'application/json',
                   'Content-Type': 'application/json'}  
  
  
  """
  #Uncomment to clear and reload square catalog
  square_items = list_items()    
  for i in square_items:
      delete_item(i["id"])
  """

  products = get_opencart_products()
  no_images = []
  for product in products:
      if not os.path.isfile(product['image']):
          no_images.append({'image': product['image'], 
                          'name' : product['name']})
  if len(no_images) > 0:
      print no_images
      raise Exception('images not found')
 
  inventory = []
  for product in products:
    variant_inventory = create_item(product)
    inventory += variant_inventory

  for i in inventory:
      update_inventory(i['variant_id'],i['quantity'])

  """
  set tax fee for all products. This can be run in isolation and does not require
  previous steps to have run first
  """
  square_items = list_items()    
  fees = get_fees()  
  fee_id = fees[0]['id']
  for square_item in square_items:
    apply_fee(square_item['id'],
              fee_id)

  connection.close()