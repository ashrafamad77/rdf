### Description of the content ###
1) Example target RDF files (manually curated). This shows our modelling approach for three dimensions of the product : 
- details (with some core properties)
- price history
- longer version of core properties

2) python script to automate the manual data modelling, and the prompt used to generate the script using AI. 
- json_to_rdf_batch.py (used for the product details)

### PROMPT USED ###
"You are an expert in modelling data to RDF. in your context, I provide you with an input a JSON file (about one product) example and the expected output in RDF. Rules : 1) You must understand the logic of the mapping between the input JSON and the output RDF. 2) you must take a look at the folder where all the input JSON files (which describe all the products) are to have a broader understanding of all the products, not just the example JSON file and its RDF conversion.  3)  you must create a python script that can convert all the JSON files in the foler /home/amad/json_to_rdf/product_details (representing all the different products, not just the example). Please note that the products belong to different categories (smartphones, connected watches, etc.) so they descriptors can vary to some extent. However, you MUST follow the logic and spirit of the example output RDF file. The idea is that all of these products will be imported into graphDB, so they must have some coherence. in the way the are modelled. Can you resume the task before you start analyzing the files and creating the python script ?"
