# Hospital Equipment Tracker 

|![Equipment Tracker Architecture](docs/images/equipment-tracker-architecture.jpeg)|
|:--:| 
|*Hospital equipment tracker overview*|

We saw in several news reports that hospitals were using spreadsheets to track medical equipment such as ventilators or beds. Over a virtual coffee, we came up with the idea to build a hospital equipment tracker using the [EVRYTHNG product cloud](https://dashboard.evrythng.com). The equipment tracker currently does two things:

- Register medical individual equipment and the product type (e.g. ICU MECHANICAL BED or Leon Plus, Neo, HLM, with Aion). Product types describe a set of equipment or stock keepign unit (SKU). Once you added equipment and product type to the EVRYTHNG product cloud, you’ll be able to monitor equipment usage and location in our  dashboard (see [video](https://storage.googleapis.com/hospital-beds-store/docs/videos/dashboard.mov))
- Track equipment availability and equipment movement using a simple web page (see [video](https://storage.googleapis.com/hospital-beds-store/docs/videos/mobile-client.mp4))

## Equipment Availability

|![Ventilator QR code](docs/images/ventilator-qr.png)|
|:--:| 
|*Open your phone camera and hold it up against this QR code. Click the link to access the page of a ventilator.*|

The equipment tracker is entirely Cloud/Web-based and the web page is accessed by scanning the individual QR code with your phone camera. Each QR is created by the EVRYTHNG product cloud so there is no need to source these from elsewhere. They are simply printed and attached to each item you would like to track.
From the equipment page you can;

- See if the equipment is available to use
- Change the status from “available” to “in-use” and vice versa
- Change the equipment location

 ## Moving equipment to new location
 
|![Ventilator QR code](docs/images/sickbay.png)|
|:--:| 
|*Move ventilator to `Sickbay`*|

Locations will be issued with a QR code, these can be associated with a ward, floor or any other location identity and would be stuck to a door, wall or other accessible place.

To assign a piece of equipment to a new location

- Scan the equipment QR code
- Select “change location” on the webpage
- Scan the QR code for the new location

  
|![Ventilator QR code](docs/images/sickbay.png)|
|:--:| 
|*Move ventilator to `Minor S&S`*|  


  

## Interested? Here is what you need to do

[me](mailto:joel@evrythng.com) 
## Initial Setup:

- Send me an email with a list (Excel, csv) of which equipment you'd like to track and all possible locations. 
- Download EQUIPMENT QR codes
    - `https://equipment-tracker-dot-machine-learning-238812.appspot.com//hospitals/{hospital_name}/equipments`.
    - You'll get pages of QR codes, which you will print and attach to your equipment.
- Download LOCATION QR codes
    - `https://equipment-tracker-dot-machine-learning-238812.appspot.com//hospitals/{hospital_name}/locations`
    - You'll get pages of QR codes, which you will print and attach to your walls or doors.
- [Register](https://dashboard.evrythng.com/signup) for an account on the EVRYTHNG platform. Send us your username (it will be your email address) and we will give you access to the master data.

<div align="center" style="text-align: center;  font-weight: bold;">NOW YOU’RE READY!</div>