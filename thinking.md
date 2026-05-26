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
- file upload avoids all the auth barriers, api option could be looked into at a later stage.
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
