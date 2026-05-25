#*processing*

---
data sources:
1. sap - fuel, manufacturing costs etc
2. utility, electricity
3. transport 
---

1 - is done with sap in most companies 
    SAP data formats - tdl []
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

##**1 . SAP MM**

- need -> PO -> receipt -> doc of what recieved -> invoicing 
- i[t is called MB51 - material document list. ](https://www.linkedin.com/posts/surya-prakash1123_sapmm-mb51-saptraining-share-7335584437251788801-QP_N/)
- we need all MB51 from date - date 

- hardships
    - sap uses german
    - what format to choose 
        - I am thinking csv as we can make use of simple SQL joins for lookup table, row level locking & normalisation 

    
---