import os
import json
from glob import glob
from collections import defaultdict

# Output directory (same as input for now)
INPUT_DIR = 'product_details'
OUTPUT_EXT = '.ttl'

# Prefixes as in the example
PREFIXES = '''@prefix schema: <http://schema.org/> .
@prefix gr: <http://purl.org/goodrelations/v1#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix findme: <http://www.findme.com/ontology/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dbr: <http://dbpedia.org/resource/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n\n'''


def safe(val, default=None):
    return val if val is not None else default

def qstr(val):
    return '"{}"'.format(str(val).replace('"', '\"'))

def iri(base, id):
    return f'<{base}{id}>'

def make_feature_iri(label):
    # CamelCase, remove accents, spaces, etc.
    import re, unicodedata
    label = unicodedata.normalize('NFKD', label).encode('ascii', 'ignore').decode('ascii')
    label = re.sub(r'[^a-zA-Z0-9]', '', label.title().replace(' ', ''))
    return f'findme:{label}'

def make_device_iri(label):
    # Similar to feature
    return make_feature_iri(label)

def write_ttl(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

def get_main_product_iri(pid):
    return f'<http://www.findme.com/data/product/{pid}>'

def get_brand_iri(bid):
    return f'<http://www.findme.com/data/brand/{bid}>'

def get_category_iri(cid):
    return f'<http://www.findme.com/data/category/{cid}>'

def get_offer_iri(oid):
    return f'<http://www.findme.com/data/offer/{oid}>'

def get_alternative_price_iri(oid):
    return f'<http://www.findme.com/data/alternativePrice/{oid}>'

def get_store_iri(sid):
    return f'<http://www.findme.com/data/store/{sid}>'

def get_payment_option_iri(name):
    return f'<http://www.findme.com/data/paymentOption/{name}>'

def get_payment_provider_iri(name):
    return f'<http://www.findme.com/data/paymentProvider/{name}>'

def get_inventory_iri(pid):
    return f'<http://www.findme.com/data/product/{pid}/inventoryLevel>'

def get_functionality_set_iri(pid):
    return f'<http://www.findme.com/data/product/{pid}/functionalitySet>'

def get_compatible_devices_iri(pid):
    return f'<http://www.findme.com/data/product/{pid}/compatibleDevices>'

def get_official_rating_iri(pid):
    return f'<http://www.findme.com/data/product/{pid}/officialRating>'

def get_user_rating_iri(pid):
    return f'<http://www.findme.com/data/product/{pid}/userRating>'

def get_offer_inventory_iri(oid):
    return f'<http://www.findme.com/data/offer/{oid}/inventoryLevel>'

def get_alternative_price_inventory_iri(oid):
    return f'<http://www.findme.com/data/alternativePrice/{oid}/inventoryLevel>'

def get_store_rating_iri(sid):
    return f'<http://www.findme.com/data/store/{sid}/rating>'

def render_category_hierarchy(category):
    lines = []
    if not category or 'path' not in category:
        return lines

    path = category['path']
    for i, cat in enumerate(path):
        cid = cat.get('id')
        name = cat.get('name')
        pathName = cat.get('pathName')
        iri = get_category_iri(cid)

        lines.append(f'{iri} a skos:Concept, schema:Category ;')
        lines.append(f'    schema:name {qstr(name)}@fr, {qstr(name)}@en ;')
        lines.append(f'    rdfs:label {qstr(name)} ;')
        lines.append(f'    findme:categoryId {qstr(cid)} ;')

        # Current category may only have full data (like logo, adultContent, etc.)
        if i == len(path) - 1:
            if 'logo' in category and category['logo']:
                lines.append(f'    schema:logo <{category["logo"]}> ;')
            if 'productCollection' in category and category['productCollection']:
                lines.append(f'    findme:productCollection {qstr(category["productCollection"])} ;')
            if 'hasAdultContent' in category:
                lines.append(f'    findme:hasAdultContent {str(category["hasAdultContent"]).lower()} ;')
            if 'pathName' in category and category['pathName']:
                lines.append(f'    schema:url {qstr(category["pathName"])} ;')
        else:
            if pathName:
                lines.append(f'    schema:url {qstr(pathName)} ;')

        # Add skos:broader link if not the root
        if i > 0:
            parent_iri = get_category_iri(path[i - 1]['id'])
            lines.append(f'    skos:broader {parent_iri} ;')

        # Close this concept
        lines[-1] = lines[-1].rstrip(' ;') + ' .\n'

    return lines

def render_feature_nodes(features):
    # features: list of (label_fr, label_en)
    lines = []
    for label_fr, label_en in features:
        iri = make_feature_iri(label_fr)
        lines.append(f'{iri} a findme:Feature ;')
        lines.append(f'    rdfs:label {qstr(label_en)}@en, {qstr(label_fr)}@fr .\n')
    return lines

def render_device_nodes(devices):
    # devices: list of (label_fr, label_en, dbpedia_uri or None)
    lines = []
    for label_fr, label_en, dbpedia_uri in devices:
        iri = make_device_iri(label_fr)
        lines.append(f'{iri} a findme:Device ;')
        lines.append(f'    rdfs:label {qstr(label_en)}@en, {qstr(label_fr)}@fr ;')
        if dbpedia_uri:
            lines.append(f'    owl:sameAs dbr:{dbpedia_uri} .\n')
        else:
            lines[-1] = lines[-1].rstrip(' ;') + ' .\n'
    return lines

def render_similar_products(similar_products):
    lines = []
    for prod in similar_products:
        pid = prod.get('id')
        if not pid:
            continue
        lines.append(f'{get_main_product_iri(pid)} a schema:Product ;')
        lines.append(f'    schema:name {qstr(prod.get("name", ""))} ;')
        lines.append(f'    rdfs:label {qstr(prod.get("name", ""))} ;')
        lines.append(f'    schema:productID {qstr(pid)} ;')
        if prod.get('pathName'):
            lines.append(f'    schema:url {qstr(prod["pathName"])} ;')
        if prod.get('description'):
            lines.append(f'    schema:description {qstr(prod["description"])} .\n')
        else:
            lines[-1] = lines[-1].rstrip(' ;') + ' .\n'
    return lines

def render_dynamic_payment_options(encountered_options):
    lines = []
    for opt in sorted(encountered_options):
        label = opt.replace('_', ' ').title()  # e.g., 'CASH_ON_DELIVERY' → 'Cash On Delivery'
        lines.append(f'{get_payment_option_iri(opt)} rdfs:label {qstr(label)} .\n')
    return lines

def process_offer_inventory(oid, stock, name, is_alternative=False):
    lines = []
    inventory_iri = get_alternative_price_inventory_iri(oid) if is_alternative else get_offer_inventory_iri(oid)
    
    lines.append(f'{inventory_iri} a schema:QuantitativeValue ;')
    lines.append(f'    rdfs:label {qstr(name + " Inventory Level")} ;')

    status = stock.get('status', '').lower()
    status_text = stock.get('statusText')

    # Add status and statusText under the findme prefix for later mapping
    if status:
        lines.append(f'    findme:stockStatus {qstr(status)} ;')

    if status_text:
        lines.append(f'    findme:stockStatusText {qstr(status_text)} ;')

    # Add fallback literal value for human-readable status (for debugging)
    lines.append(f'    schema:value {qstr(status)} .\n')
    
    return lines

def process_offer_or_alternative_price(oid, price_data, is_alternative=False):
    lines = []
    iri_func = get_alternative_price_iri if is_alternative else get_offer_iri
    offer_iri = iri_func(oid)
    
    # Type and basic info
    rdf_type = "schema:Offer" if not is_alternative else "findme:AlternativePrice"
    lines.append(f'{offer_iri} a {rdf_type} ;')
    lines.append(f'    schema:name {qstr(price_data.get("name", ""))} ;')
    lines.append(f'    rdfs:label {qstr(price_data.get("name", ""))} ;')
    
    # Process pricing info
    if price_data.get('price'):
        price_info = price_data['price']
        if price_info.get('inclShipping') is not None:
            lines.append(f'    schema:price "{price_info["inclShipping"]}"^^xsd:decimal ;')
        if price_info.get('exclShipping') is not None:
            lines.append(f'    findme:priceExcludingShipping "{price_info["exclShipping"]}"^^xsd:decimal ;')
    
    # Condition
    if price_data.get('condition'):
        lines.append(f'    schema:itemCondition schema:NewCondition ;')
    
    # Inventory
    inventory_iri = get_alternative_price_inventory_iri(oid) if is_alternative else get_offer_inventory_iri(oid)
    lines.append(f'    schema:inventoryLevel {inventory_iri} ;')
    
    # Store reference (only for main offers, not for alternative prices)
    if not is_alternative and price_data.get('store'):
        store = price_data['store']
        lines.append(f'    schema:seller {get_store_iri(store["id"])} ;')
    
    # Common properties
    lines.append(f'    findme:shopOfferId {qstr(oid)} ;')
    if price_data.get('ourChoiceScore') is not None:
        lines.append(f'    findme:ourChoiceScore {price_data["ourChoiceScore"]} ;')
    if price_data.get('authorizedDealer') is not None:
        lines.append(f'    findme:authorizedDealer {str(price_data["authorizedDealer"]).lower()} ;')
    if price_data.get('primaryMarket') is not None:
        lines.append(f'    findme:primaryMarket {str(price_data["primaryMarket"]).lower()} ;')
    if price_data.get('externalUri'):
        lines.append(f'    findme:externalUri <{price_data["externalUri"]}> ;')
    
    # Shipping details
    shipping = price_data.get('shipping', {})
    if shipping and isinstance(shipping, dict):
        cheapest = shipping.get('cheapest', {})
        if cheapest and isinstance(cheapest, dict):
            if cheapest.get('shippingCost') is not None:
                lines.append(f'    findme:shippingCost "{cheapest["shippingCost"]}"^^xsd:decimal ;')
            if cheapest.get('sustainability'):
                lines.append(f'    findme:shippingSustainability {qstr(cheapest["sustainability"])} ;')
            if cheapest.get('eligibility'):
                lines.append(f'    findme:shippingEligibility {qstr(cheapest["eligibility"])} ;')
            if cheapest.get('deliveryMethod'):
                lines.append(f'    findme:shippingMethod {qstr(cheapest["deliveryMethod"])} ;')
            if cheapest.get('carrier'):
                lines.append(f'    findme:shippingCarrier {qstr(cheapest["carrier"])} ;')
            if cheapest.get('deliveryDays'):
                lines.append(f'    findme:shippingDeliveryDays {qstr(cheapest["deliveryDays"])} ;')
    
    # Variant info
    variant = price_data.get('variantInfo', {})
    if variant.get('size'):
        lines.append(f'    findme:size {qstr(variant["size"])} ;')
    if variant.get('colors'):
        colors = variant['colors']
        if isinstance(colors, list) and colors:
            lines.append(f'    findme:color {qstr(colors[0])} ;')
    if variant.get('sizeSystem'):
        lines.append(f'    findme:sizeSystem {qstr(variant["sizeSystem"])} ;')
    
    # Close the entity
    lines[-1] = lines[-1].rstrip(' ;') + ' .\n'
    
    return lines


def process_file(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    product = data['data']['product']
    pid = product['id']
    ttl_lines = [PREFIXES]

    encountered_payment_options = set()  # <--- This is per-file scoped

    # Main Product Node
    main_iri = get_main_product_iri(pid)
    ttl_lines.append(f'{main_iri} a schema:Product ;')
    ttl_lines.append(f'    schema:name {qstr(product["name"])} ;')
    ttl_lines.append(f'    rdfs:label {qstr(product["name"])} ;')
    ttl_lines.append(f'    schema:productID {qstr(pid)} ;')
    ttl_lines.append(f'    schema:url {qstr(product.get("pathName", ""))} ;')
    
    # Brand
    brand = product.get('brand')
    if brand:
        ttl_lines.append(f'    schema:brand {get_brand_iri(brand["id"])} ;')
    
    # Inventory
    #ttl_lines.append(f'    gr:hasInventoryLevel {get_inventory_iri(pid)} ;')
    
    # MainEntityOfPage
    hrefs = product.get('hrefLang', [])
    if hrefs:
        ttl_lines.append('    schema:mainEntityOfPage ' + ',\n        '.join(f'<{h["url"]}>' for h in hrefs) + ' ;')
    
    # Ratings
    agg_summary = product.get('aggregatedRatingSummary')
    agg = None
    if agg_summary and isinstance(agg_summary, dict):
        summary = agg_summary.get('summary')
        if summary and isinstance(summary, dict):
            agg = summary.get('rating')
    if agg:
        ttl_lines.append(f'    schema:aggregateRating {get_official_rating_iri(pid)} ;')
    if product.get('userReviewSummary'):
        ttl_lines.append(f'    schema:aggregateRating {get_user_rating_iri(pid)} ;')
    
    # Features/Compatibility (coreProperties)
    core_props = product.get('coreProperties', {}).get('nodes', [])
    feature_labels = []
    device_labels = []
    
    for prop in core_props:

        if prop['__typename'] == "PropertyBoolean":
            # Ex: findme:hasDisplay true    
            value, name = str(prop.get('boolean')).lower(), prop['name']
            name = "".join([n.capitalize() for n in name.split()])
            ttl_lines.append(f'    findme:has{name} {value} ;')

        if prop['__typename'] == 'PropertyList' and prop['name'].lower().startswith('fonctionnalit'):
            # Features
            feature_labels = [(v, v) for v in prop.get('values', [])]
            ttl_lines.append(f'    findme:hasFunctionalitySet {get_functionality_set_iri(pid)} ;')
        elif prop['__typename'] == 'PropertyList' and 'compatible' in prop['name'].lower():
            # Compatible devices
            device_labels = [(v, v, None) for v in prop.get('values', [])]
            ttl_lines.append(f'    findme:hasCompatibleDeviceSet {get_compatible_devices_iri(pid)} ;')
    
    
    # Category
    category = product.get('category')
    if category:
        ttl_lines.append(f'    schema:category {get_category_iri(category["id"])} ;')
    
    # Media
    media = product.get('media', {})
    if media.get('first'):
        ttl_lines.append(f'    schema:image <{media["first"]}> ;')
        ttl_lines.append(f'    findme:primaryImage <{media["first"]}> ;')
    if media.get('count') is not None:
        ttl_lines.append(f'    findme:mediaCount {media["count"]} ;')
    
    # Popularity
    pop = product.get('popularity', {})
    if pop.get('total') is not None:
        ttl_lines.append(f'    findme:totalPopularity "{pop["total"]}"^^xsd:integer ;')
    if pop.get('inCategory') is not None:
        ttl_lines.append(f'    findme:categoryPopularityRank "{pop["inCategory"]}"^^xsd:integer ;')
    
     # Product Inventory
    stock_status = product.get('stockStatus', 'in_stock')  # Default to 'in_stock' if missing
    status_text = product.get('stockText', '')  # If applicable, you can add stockText or similar
    ttl_lines.append(f'    findme:productStockStatus {qstr(stock_status)} ;')
    if status_text:
        ttl_lines.append(f'    findme:productStockStatusText {qstr(status_text)} ;')


    # Offers
    offers = []
    offer_ids = set()
    for offer in product.get('prices', {}).get('nodes', []):
        oid = offer.get('shopOfferId')
        if oid:
            offers.append(get_offer_iri(oid))
            offer_ids.add(oid)
    if offers:
        ttl_lines.append('    schema:offers ' + ',\n                 '.join(offers) + ' ;')
    
    # Similar Products
    simprods = product.get('popularProducts', [])
    if simprods:
        simprod_iris = [get_main_product_iri(p['id']) for p in simprods if 'id' in p]
        if simprod_iris:
            ttl_lines.append('    schema:isSimilarTo ' + ',\n        '.join(simprod_iris) + ' ;')
    
    # End product node
    ttl_lines[-1] = ttl_lines[-1].rstrip(' ;') + ' .\n'


    # Ratings Nodes
    if agg:
        ttl_lines.append(f'{get_official_rating_iri(pid)} a schema:AggregateRating ;')
        ttl_lines.append(f'    rdfs:label "Official Rating: {agg.get("score", "")}/5" ;')
        ttl_lines.append(f'    findme:officialRating "{agg.get("score", "")}"^^xsd:float ;')
        ttl_lines.append(f'    schema:ratingValue "{agg.get("score", "")}"^^xsd:float ;')
        ttl_lines.append(f'    schema:ratingCount "{agg.get("count", "")}"^^xsd:integer .\n')
    
    user = product.get('userReviewSummary', {})
    if user and isinstance(user, dict) and user.get('rating') is not None:
        ttl_lines.append(f'{get_user_rating_iri(pid)} a schema:AggregateRating ;')
        ttl_lines.append(f'    rdfs:label "User Rating: {user.get("rating", "")}/5" ;')
        ttl_lines.append(f'    findme:userReviewScore "{user.get("rating", "")}"^^xsd:float ;')
        ttl_lines.append(f'    schema:ratingValue "{user.get("rating", "")}"^^xsd:float ;')
        ttl_lines.append(f'    schema:reviewCount "{user.get("count", "")}"^^xsd:integer .\n')
    
    # Brand Node
    if brand:
        ttl_lines.append(f'{get_brand_iri(brand["id"])} a schema:Brand ;')
        ttl_lines.append(f'    schema:name {qstr(brand["name"])} ;')
        ttl_lines.append(f'    rdfs:label {qstr(brand["name"])} ;')
        ttl_lines.append(f'    findme:brandId "{brand["id"]}"^^xsd:integer ;')
        ttl_lines.append(f'    findme:isFeatured {str(brand.get("featured", False)).lower()} ;')
        if brand.get('pathName'):
            ttl_lines.append(f'    schema:url {qstr(brand["pathName"])} ;')
        ttl_lines[-1] = ttl_lines[-1].rstrip(' ;') + ' .\n'
    
    # Category Hierarchy
    if category:
        ttl_lines += render_category_hierarchy(category)
    
    # Functionality Set Node
    if feature_labels:
        ttl_lines.append(f'{get_functionality_set_iri(pid)} a findme:FunctionalitySet ;')
        ttl_lines.append(f'    rdfs:label {qstr(product["name"] + " Features")} ;')
        ttl_lines.append(f'    findme:setId "3666" ;')
        ttl_lines.append(f'    findme:forProduct {main_iri} ;')
        ttl_lines.append('    findme:includesFeature ' + ',\n        '.join([make_feature_iri(f[0]) for f in feature_labels]) + ' .\n')
        # Feature Nodes
        ttl_lines += render_feature_nodes([(f[0], f[0]) for f in feature_labels])
    
    # Compatible Device Set Node
    if device_labels:
        ttl_lines.append(f'{get_compatible_devices_iri(pid)} a findme:CompatibleDeviceSet ;')
        ttl_lines.append(f'    rdfs:label {qstr("Compatible Devices for " + product["name"])} ;')
        ttl_lines.append('    findme:includesDevice ' + ',\n        '.join([make_device_iri(d[0]) for d in device_labels]) + ' .\n')
        # Device Nodes
        ttl_lines += render_device_nodes([(d[0], d[0], None) for d in device_labels])
    
    # Process main offers and their alternative prices
    for offer in product.get('prices', {}).get('nodes', []):
        oid = offer.get('shopOfferId')
        if not oid:
            continue
        
        # Process main offer
        ttl_lines += process_offer_or_alternative_price(oid, offer)
        
        # Process inventory for main offer
        stock = offer.get('stock', {})
        ttl_lines += process_offer_inventory(oid, stock, offer.get('name', ''))

        # Process alternative prices if they exist
        alternative_prices = offer.get('alternativePrices', [])
        alternative_price_iris = []
        
        for alt_price in alternative_prices:
            alt_oid = alt_price.get('shopOfferId')
            if not alt_oid:
                continue
                
            # Add alternative price to the list for linking to main offer
            alt_price_iri = get_alternative_price_iri(alt_oid)
            alternative_price_iris.append(alt_price_iri)
            
            # Process alternative price
            ttl_lines += process_offer_or_alternative_price(alt_oid, alt_price, is_alternative=True)
            
            # Process inventory for alternative price
            alt_stock = alt_price.get('stock', {})
            ttl_lines += process_offer_inventory(alt_oid, alt_stock, alt_price.get('name', ''), is_alternative=True)
        
        # Link main offer to its alternative prices
        if alternative_price_iris:
            main_offer_iri = get_offer_iri(oid)
            ttl_lines.append(f'{main_offer_iri} findme:hasAlternativePrice {", ".join(alternative_price_iris)} .\n')

        # Store Node
        store = offer.get('store')
        if store:
            ttl_lines.append(f'{get_store_iri(store["id"])} a schema:Organization ;')
            ttl_lines.append(f'    schema:name {qstr(store["name"])} ;')
            ttl_lines.append(f'    rdfs:label {qstr(store["name"])} ;')
            if store.get('pathName'):
                ttl_lines.append(f'    schema:url <https://ledenicheur.fr{store["pathName"]}> ;')
            ttl_lines.append(f'    findme:storeId {store["id"]} ;')
            if store.get('countryCode'):
                ttl_lines.append(f'    findme:countryCode {qstr(store["countryCode"])} ;')
            if store.get('currency'):
                ttl_lines.append(f'    findme:currency {qstr(store["currency"])} ;')
            if store.get('market'):
                ttl_lines.append(f'    findme:market {qstr(store["market"])} ;')
            if store.get('primaryMarket'):
                ttl_lines.append(f'    findme:primaryMarket {qstr(store["primaryMarket"])} ;')
            if store.get('featured') is not None:
                ttl_lines.append(f'    findme:featured {str(store["featured"]).lower()} ;')
            if store.get('hasLogo') and store.get('logo'):
                ttl_lines.append(f'    schema:logo <{store["logo"]}> ;')
            if store.get('generalInformation'):
                for info in store['generalInformation']:
                    if info:
                        ttl_lines.append(f'    findme:generalInformation {qstr(info)} ;')
            if store.get('marketplace') is not None:
                ttl_lines.append(f'    findme:marketplace {str(store["marketplace"]).lower()} ;')
            
            # Store rating
            if store.get('userReviewSummary'):
                ttl_lines.append(f'    schema:aggregateRating {get_store_rating_iri(store["id"])} ;')
            
            # Payment options
            payment = store.get('payment', {})
            if payment.get('providers'):
                for prov in payment['providers']:
                    ttl_lines.append(f'    schema:paymentAccepted {get_payment_provider_iri(prov["name"])} ;')

            if payment.get('options'):
                for opt in payment['options']:
                    opt_name = opt['name']
                    ttl_lines.append(f'    findme:paymentOptions {get_payment_option_iri(opt_name)} ;')
                    encountered_payment_options.add(opt_name)

            ttl_lines[-1] = ttl_lines[-1].rstrip(' ;') + ' .\n'

            
            # Store rating node
            if store.get('userReviewSummary'):
                rating = store['userReviewSummary']
                ttl_lines.append(f'{get_store_rating_iri(store["id"])} a schema:AggregateRating ;')
                ttl_lines.append(f'    rdfs:label "{store["name"]} Rating" ;')
                ttl_lines.append(f'    schema:ratingValue "{rating.get("rating", 0)}"^^xsd:float ;')
                ttl_lines.append(f'    schema:reviewCount "{rating.get("count", 0)}"^^xsd:integer .\n')
    
    # Similar Products
    ttl_lines += render_similar_products(product.get('popularProducts', []))
    
    # Payment Options (dynamic)
    ttl_lines += render_dynamic_payment_options(encountered_payment_options)
    
    return '\n'.join(ttl_lines)

def main():
    for json_file in glob(os.path.join(INPUT_DIR, '*.json')):
        ttl_content = process_file(json_file)
        ttl_file = os.path.splitext(json_file)[0] + OUTPUT_EXT
        write_ttl(ttl_file, ttl_content)

if __name__ == '__main__':
    main() 
