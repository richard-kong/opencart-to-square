# opencart-to-square
Script to migrate product catalog from Opencart to Square POS. Just change the variables at the top of the script and run.

## Assumptions:
1. All opencart catagories are already in Square
2. Opencart database tables are prefixed with "oc_"

## Script actions

1. Queries the opencart mysql data for a list of products
2. Checks that the main image for all products actually exist
3. Converts the product data into Square's Product/Variant structure
4. Creates the product with it's variants in Square with inventory enabled
5. Updates the inventory of each product
6. Uploads and assigns master image for each product based on opencart's main image
7. Enables tax fee on all products

## Limitations:
1. Assumes all opencart catagories already exists in square
2. Where a product has multiple options, inventory is not recorded correctly since opencart does not record this
3. Assumes Tax fee is the first fee in the list
4. Cannot resume a migration, all products have to be deleted and migration needs to start again. But, updating of tax fees can be done in isolation.

