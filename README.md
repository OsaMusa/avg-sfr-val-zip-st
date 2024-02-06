# Overview
In the United States, housing has become increasingly expensive. This project was done to help share and visualize these changes. This site was created using Streamlit, a Python library for creating web applications for your visualizations. There are some limitations in the behavior of these visualizations, but the end result still convays the intended message.

There is filter for visitors to select the areas they want view that is present on each page. The states of each input widget are saved to avoid needing to re-enter selections or redo toggles when going from one page to another. Your selections are synced on all pages. 

For the sake of performance, visitors are only able to look at one metroplex at a time. When chosing a metroplex, the filter defaults to viewing one county. Visitors can view data for all counties in their chosen metroplex, but can expect a bit of a drop in performance.

## The Data
The home values provided are the average price of a single family residence at the ZIP code level. The data in this site is provided by Zillow Group and is updated monthly. These values are recorded on the last day of the month and typically made available two weeks after the date. This data dates back to January, 2000; thus, home values before then are not included.

## The Visualizations
### Heat Maps
The heat map page shows how the average property values of differnt ZIP codes compare through their color. In an effort to show how ZIP codes with similar values compare to one another, there is a 3D option available. Visitors can select the date for the values to be displayed in the heat map. As a bonus, the Heat Map page also displays the lowest, highest, and median valued ZIP codes for the date selected.

### 2D Heat Map
![2D Heat Map Example](/images/2D%20Heat%20Map%20Example.jpg)

### 3D Heat Map
![3D Heat Map Example](/images/3D%20Heat%20Map%20Example.jpg)

### Historic Values
This page has a line chart for better visualizing how the values in your chosen location have changed over time. Visitors can also select a timeframe for the visualization.
