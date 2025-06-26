# World Happiness Visualization Tool

An interactive data visualization tool built with Python and PyQt6 to explore the 2023 World Happiness Report. This project helps users investigate the global distribution of happiness and its relationship to socioeconomic factors like GDP, social support, and life expectancy.

## 📊 Features

### 🌍 Map View
- Choropleth map colored by happiness scores across 138 countries.
- Hover tooltips showing 14 key variables influencing happiness.
- Gray coloring for countries with missing data.
- Red highlight for selected countries.

### ⚪ Bubble Chart View
- Interactive scatterplot with bubble size proportional to population.
- X-axis variable selectable via buttons (e.g., GDP, social support).
- Y-axis is always happiness score.
- Color indicates happiness score using a perceptually uniform colormap.
- Hover tooltips and click-to-highlight functionality.

### 🔄 Linked Brushing View
- Two side-by-side bubble charts with linked selections.
- Dropdowns to customize axes, bubble size, and color.
- Brushing allows users to compare regions across variable combinations.
- Toggleable legends and tooltips for clarity.

### 🧭 User Interface
- Clean and intuitive PyQt6 GUI.
- Seamless switching between views.
- Controls for selecting and customizing variables per view.

## 🔍 Key Questions Explored
- What factors have the strongest impact on happiness?
- Which countries rank highest and lowest, and why?
- Are there regional patterns or trends?
- How do socioeconomic variables relate to happiness levels?

## 🧱 Technology Stack

- **Python 3**
- **PyQt6**
- **Matplotlib**
- **Pandas, NumPy**
- **GeoPandas, Shapely**
- **Pycountry**
- **Textwrap**

## 🗂️ Data Sources

- [World Happiness Report 2023 (Kaggle)](https://www.kaggle.com/datasets/ajaypalsinghlo/world-happiness-report-2023)
- `world_map.json` (used for map geometry)

## 🚀 Getting Started

### Prerequisites

Install the required Python packages:

```bash
pip install pyqt6 matplotlib geopandas pandas numpy shapely pycountry textwrap
```

### Run the App
1. Place `world_map.json` and `WHR2023.csv` in the same directory as the script.
2. Ensure the `Icons\` folder contains the required icons (e.g., `ToggleButtonOn.png`).
3. Run the application:

```bash
python toggle.py
```

### Usage
- App launches in full-screen.
- Use the navigation panel to switch views.
- Explore charts with tooltips, legends, dropdowns, and brushing tools.

## ⚠️ Known Challenges
- Axis label misalignment on bubble chart updates.
- Hover tooltip quirks in brushing view.
- Rendering issues on the map for small or narrow countries.
- Data merging between files required careful handling.

## 👥 Authors
- Danial Tleuzhanov
- Allison Nguyen
