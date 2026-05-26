# *processing*

---
data sources:
1. sap - fuel, manufacturing costs etc
2. utility, electricity
3. transport 
---

1 - is done with sap in most companies 
    SAP data formats - tdl [x]
    - sap mm - materials management
 

2 - does tsspdcl offer api for electricity bill ? 
    no but there is bbps

3 - navan and concur have an api - 
    but how do i maintain multi tenacy ?
    should take api creds from org ?

`whats the best way - api / files ?`
I would stick with files as i do not have any of these accounts
business perspective - easier onboarding and offboarding

---

## 1 . SAP MM

- need -> PO -> receipt -> doc of what recieved -> invoicing 
- [it is called MB51 - material document list. ](https://www.linkedin.com/posts/surya-prakash1123_sapmm-mb51-saptraining-share-7335584437251788801-QP_N/)
- we need all MB51 from date - date 

- hardships
    - SAP uses german
        - we need header normalization
    - ~~what format to choose ~~
        - I am thinking csv as we can make use of simple SQL joins for lookup table, row level locking & normalisation 
    - can have malformed data, missing columns etc
    - need to understand codes in SAP

    - MATKL - material group
    - MEINS - units of measurement 
    these are critical
    
---

---

## 2 . Utility data, electricity

- I am assuming TSSPDCL for the exercise
- bbps is just for paying bills so resorting to csv is the right approach

- hardships 
    - no proper dating (not monthly exactly)
    - normalizing the units
    - multiple meters
    - emission categories
    - generator when power off
---

---
## 3 . Travel - navan, concur

- flight, hotels, on road
- [file upload avoids all the auth barriers, api option could be looked into at a later stage.](https://www.graphed.com/blog/how-to-export-concur-report-to-excel)
- **hotels** - identify country and star rating
- **on road**- use spend based calculation
- dont use builtin **carbon_kg** - might differ from our calculations

- navan/concur has 2 types of exports 
    1. iternary report
    2. audit report - we will use this as it account for only taken trips

- hardships
    - no distances only airport codes.
    - can be connecting flights - flag routes
    - class of travel matters although it is the same flight
    - multiple currencies
    - gap might be present eg: makemytrip
---


`challenge right now -`
---
enforcing internal schema and tracability
---

Rough - timeline

data modelling - 

3 tables for each ingestion - sap, power, travel

canonical table for internal consistency

- we will have a single table that is populated throught 3 sources
- never delete the original unnormalised data
- create columns for normalised data
- enforce id's and keys
- implementing audit log using row level locking

### skipping 
- ocr
- auto schema inference
- iternary reconstruction

should think of :
- flagging missing data/gaps

---
## **finalising decissions**

sile upload -> source file -> parsing + normalisation (canonical form) -> scan for suspisions (draft rules) -> audit lock

tables:
- organisation - diff branches
- lookup table
- types & units
- source file - out of three, by who, no of rows etc
- raw file (shouldn't edit)
- canonical table - 3
- audit table (shouldn't edit)
---

instead of only 1 canonical table - split into 3 
1. SAP - material & quantity centric
2. utility - kwtt consumed 
3. commute - payment centric 
'calculating the emission acc to this simplified approach for version 1'

---
#### Rules for suspicion flagging -
negative values
mismatch in units
unknown codes
duplicate row
gap in dates
---