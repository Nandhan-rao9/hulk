# DECISIONS

## SAP Source

### format - I chose: MB51 flat CSV export

why - I could find most people use this irl and the client teams can export this format easily. I also found it has the right level of detail for our demo. (https://www.linkedin.com/posts/surya-prakash1123_sapmm-mb51-saptraining-share-7335584437251788801-QP_N/)

The subset I'm handling - 
- movement type 101 (goods receipts) only
- material documents with WERKS, MATNR, MATKL fields
 
What I ignored -
- returns (BWART 122)
- transfers (BWART 311)
 - I chose to ignore these because they are less common and would add complexity to our demo.

## Utility Source

### format - I chose: TSSPDCL portal CSV export

because - I am from telangana and this is a common format used by state government utility authorities.

The subset I'm handling -
- Different meters of one org.
- addressing gaps in bills.

what I ignored -
- pdf bill parsing, as it would add a lot of complexity and we can get the same data from the csv export.

## Travel Source

### format - I chose: Both Concur and Navan CSV exports

because - these are the two most common travel management platforms used by enterprises, and supporting both would make our demo more comprehensive and realistic.

- i had to build forex conversion to normalise.

The subset I'm handling -
- flights and different classes of flights (economy, business, first class).
- hotels with different star ratings.
- car rentals with spend as factor.

What I ignored -
- recalculating flight stalls and paths.
- taking into account every factor in hotel stay, like food orders, amenities used, etc.
- resorted back to simple rule based calculations for car rentals instead of trying to build a complex model that takes into account all the factors for demo.

[link](https://greenly.earth/en-gb/blog/company-guide/spend-based-method-vs-activity-based-method-our-methodology)


## Workflow - 

I chose 4 - flagged, pending, pending for admin approval, approved.

This is a realtime moxk of what Veeva systems uses for their platform.

## Duplicate Detection - 

hashing the content of file and storing it.

## Unit normalisation -

UI says you have to have those names specifically as column headers, but it is a bit flexible and if the name is close enough it will suffice.

## Ingestion

I chose the approached specified above(CSV) rather than API because it is easier to onboard and offboard as we are not trying to maintain 0 latency or realtime sync for the project.

If I can I would love to do API integration in the future as it would be more seamless and would allow for more real time data syncing.

## Immutability -

I chose **soft immutability** bacause it was getting annoying in dev environment.

## Emission calculations - 

I chose to do it on ingestion.
I used the DEFRA 2024 emission factors because they were the stable baseline chosen for this implementation.

For the scope of this assignment, I intentionally simplified certain domain-specific calculation edge cases and focused on building a reliable, extensible ingestion and calculation pipeline.


Along the way, I made many workaouunds for development and deployment like switching to railway for frontend too instead of vercel to avoid cors error.



What I would ask the PM if I had the chance -
1. For SAP data, should we also handle returns (BWART 122) and transfers (BWART 311), or focus only on goods receipts (BWART 101) for this demo?
2. What emission factors should we use long term? Should we stick with DEFRA 2024 for consistency, or consider more region-specific factors for accuracy?
3. How to architect the lookup tables for emission factors? Should we have separate tables for each scope and source, or a unified table with source/scope as dimensions?
4. should we implement partial row ingestion.

