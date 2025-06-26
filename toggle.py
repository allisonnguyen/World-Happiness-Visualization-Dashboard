import sys
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QGraphicsDropShadowEffect, QGridLayout, QMainWindow, QSlider, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QStackedWidget, QLabel
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QColor
from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
from matplotlib.widgets import RectangleSelector
import shapely.geometry
import geopandas as gpd
import pandas as pd
import numpy as np
import pycountry
import textwrap

''' -------- Helper Functions -------- '''
def wrap_title(title, max_len=40):
    return '\n'.join(textwrap.wrap(title, width=max_len))

def add_size_legend(ax, size_data, size_attr, scale_factor):
        size_min, size_max = size_data.min(), size_data.max()
        size_values = np.linspace(size_min, size_max, num=3)

        size_markers = 50 + ((size_values - size_min) / (size_max - size_min)) * 950
        size_markers *= scale_factor / 50

        legend_width = len(size_values) * 1.5
        center_x = legend_width / 2 - 0.75

        ax.text(
            center_x, 0.8,
            size_attr,
            fontsize=12,
            ha='center',
            va='center',
            weight='bold'
        )

        ax.text(
            -0.5, 0,
            "Smaller\npopulation",
            fontsize=10,
            ha='right',
            va='center',
            weight='bold'
        )
        ax.text(
            len(size_values) + 0.2, 0,
            "Larger\npopulation",
            fontsize=10,
            ha='left',
            va='center',
            weight='bold'
        )

        for i, (val, marker) in enumerate(zip(size_values, size_markers)):
            ax.scatter(
                [i * 1.2], [0],
                s=marker,
                color='gray',
                alpha=0.6,
                edgecolors='black',
            )

        ax.set_xlim(-2, legend_width + 1)
        ax.set_ylim(-0.5, 1)
        ax.axis('off')

def add_dynamic_size_legend(ax, size_data, size_attr, scale_factor):
        size_min, size_max = size_data.min(), size_data.max()
        size_values = np.linspace(size_min, size_max, num=3)
        
        size_markers = 50 + ((size_values - size_min) / (size_max - size_min)) * 950
        size_markers *= scale_factor / 50

        legend_elements = [
            plt.Line2D(
                [0], [0],
                marker='o',
                color='w',
                label=f"{val:.1f}",
                markersize=np.sqrt(marker),
                markerfacecolor='gray',
                markeredgecolor='k'
            )
            for val, marker in zip(size_values, size_markers)
        ]

        legend_title = f"{size_attr}"
        return ax.legend(
            handles=legend_elements,
            title=legend_title,
            loc='upper right',
            frameon=True,
            handleheight=3.5,
            handletextpad=1.5,
            borderpad=0.7,
        )

''' -------- Bubble Chart App -------- '''
class BubbleChart(QWidget):
    def __init__(self):
        super().__init__()

        self.worldmap = gpd.read_file("world_map.json", driver='GeoJSON')

        self.data = pd.read_csv("WHR2023.csv")   
        excluded_column = 'Ladder score in Dystopia'
        self.data = self.data.loc[:, self.data.columns != excluded_column]
        country_to_code = {country.name: country.alpha_3 for country in pycountry.countries}
        
        self.data['Country code'] = self.data['Country name'].map(country_to_code)

        manual_mapping = {
            "Taiwan Province of China": "TWN",
            "Kosovo": "XKX",
            "South Korea": "KOR",
            "Moldova": "MDA",
            "Vietnam": "VNM",
            "Bolivia": "BOL",
            "Russia": "RUS",
            "Hong Kong S.A.R. of China": "HKG",
            "Congo (Brazzaville)": "COG",
            "Congo (Kinshasa)": "COD",
            "Venezuela": "VEN",
            "Laos": "LAO",
            "Ivory Coast": "CIV",
            "State of Palestine": "PSE",
            "Iran": "IRN",
            "Turkiye": "TUR",
            "Tanzania": "TZA",
        }
        self.data['Country code'] = self.data['Country code'].fillna(self.data['Country name'].map(manual_mapping))

        # Map population estimates from worldmap to data
        self.worldmap['pop_est'] = self.worldmap['pop_est'].fillna(0)
        pop_est_mapping = dict(zip(self.worldmap['adm0_a3'], self.worldmap['pop_est']))
        self.data['pop_est'] = self.data['Country code'].map(pop_est_mapping)
        self.data = self.data.dropna(subset=["Logged GDP per capita", "Ladder score", "pop_est"])

        layout = QVBoxLayout(self)

        self.attributes = {
            "Logged GDP per capita": ("Less wealth", "More wealth"),
            "Social support": ("Less social support", "More social support"),
            "Healthy life expectancy": ("Shorter life", "Longer life"),
            "Freedom to make life choices": ("Less freedom", "More freedom"),
            "Generosity": ("Less generous", "More generous"),
            "Perceptions of corruption": ("Less corruption", "More corruption")
        }

        button_layout = QHBoxLayout()
        self.buttons = []
        
        for attr in self.attributes.keys():
            button = QPushButton(attr)
            self.buttons.append(button)
            button.clicked.connect(lambda checked, a=attr, b=button: self.on_button_click(a, b))
            button_layout.addWidget(button)

        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)

        layout.addWidget(NavigationToolbar(self.canvas, self))
        layout.addWidget(self.canvas)
        layout.addLayout(button_layout)

        self.update_button_styles(self.buttons[0])
        self.selected_indices = set()
        self.edgecolors = ["white"] * len(self.data)
        self.linewidths = [0.5] * len(self.data)

        self.cbar = None
        self.left_label = None
        self.right_label = None

        self.tooltip = QLabel(self)
        self.tooltip.setStyleSheet("background-color: white; border-radius: 15px; padding: 5px;")
        self.tooltip.setFixedSize(225, 63)
        self.tooltip.move(50, 50)
        shadow = QGraphicsDropShadowEffect(self.tooltip)
        shadow.setBlurRadius(15)
        shadow.setOffset(5, 5)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.tooltip.setGraphicsEffect(shadow)
        self.tooltip.hide()

        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.canvas.mpl_connect('button_press_event', self.on_click)

        self.update_data("Logged GDP per capita")
        self.ax.set_position([0.1, 0.25, 0.8, 0.6])
        self.canvas.draw()
        self.position_colorbar_labels()
    
    def on_button_click(self, attribute, button):
        self.update_data(attribute)
        self.update_button_styles(button)
    
    def update_data(self, x_attribute):
        self.ax.clear()
        x = self.data[x_attribute]
        y = self.data["Ladder score"]
        color = self.data["Ladder score"]

        size = self.data["pop_est"]
        size = size.clip(lower=0)
        size_scaled = 50 + ((size - size.min()) / (size.max() - size.min())) * 950
        size_scaled *= 100 / 50

        self.ax.set_position([0.1, 0.25, 0.8, 0.6])

        self.scatter = self.ax.scatter(
            x, y,
            s=size_scaled,
            c=color,
            cmap="viridis",
            alpha=0.6,
            edgecolors=self.edgecolors,
            linewidths=self.linewidths
        )

        self.ax.set_ylim([y.min() - 5, y.max() + 5])
        self.ax.axis('off')

        left_label, right_label = self.attributes[x_attribute]
        self.ax.text(
            x.min() - (x.max() - x.min()) * 0.1,
            y.mean(),
            left_label, 
            fontsize=10, 
            ha='center', 
            va='center', 
            color="black",
            weight="heavy"
        )
        self.ax.text(
            x.max() + (x.max() - x.min()) * 0.1,
            y.mean(),
            right_label, 
            fontsize=10, 
            ha='center', 
            va='center', 
            color="black",
            weight="heavy"
        )
        self.ax.set_title(f"{x_attribute}", fontsize=18, weight='bold', pad=20)

        if self.cbar is None:
            self.cbar = self.figure.colorbar(self.scatter, ax=self.ax, orientation="horizontal", fraction=0.03)
        else:
            self.cbar.update_normal(self.scatter)

        self.cbar.ax.set_position([0.55, 0.12, 0.4, 0.02])
        self.cbar.set_ticks([])

        if hasattr(self, "size_legend_ax"):
            self.size_legend_ax.remove()
        self.size_legend_ax = self.figure.add_axes([0.05, 0.08, 0.4, 0.15])
        add_size_legend(self.size_legend_ax, self.data["pop_est"], "Population Size", scale_factor=100)

        self.position_colorbar_labels()

        self.canvas.draw()

    def on_hover(self, event):
        if event.inaxes != self.ax:
            self.tooltip.hide()
            return
        
        cont, ind = self.scatter.contains(event)
        if cont:
            hovered_index = ind["ind"][0]

            country_name = self.data.iloc[hovered_index]["Country name"]
            ladder_score = self.data.iloc[hovered_index]["Ladder score"]

            details = f"""
            <div style="line-height: 1.15;">
                <b>{country_name}</b><br>
                Happiness Score: {ladder_score:.2f}
            </div>
            """
            self.tooltip.setStyleSheet("""
                background-color: white;
                border-radius: 15px;
                padding: 10px;
                color: black;
                font-size: 16px;
            """)
            self.tooltip.setText(details)
            self.tooltip.adjustSize()
            self.tooltip.show()

            global_pos = self.canvas.mapToGlobal(event.guiEvent.pos())
            local_pos = self.mapFromGlobal(global_pos)

            mouse_x = local_pos.x()
            mouse_y = local_pos.y()
            tooltip_width = self.tooltip.width()
            tooltip_height = self.tooltip.height()

            offset_x = 20
            offset_y = 20

            window_geometry = self.geometry()
            window_width, window_height = (
                window_geometry.width(),
                window_geometry.height(),
            )

            if mouse_x + offset_x + tooltip_width > window_width:
                offset_x = -tooltip_width - 20
            if mouse_y + offset_y + tooltip_height > window_height:
                offset_y = -tooltip_height - 20

            if mouse_x + offset_x < 0:
                offset_x = 20
            if mouse_y + offset_y < 0:
                offset_y = 20

            new_x = mouse_x + offset_x
            new_y = mouse_y + offset_y

            self.tooltip.move(new_x + 5, new_y + 5)

            hover_edgecolors = self.edgecolors[:]
            hover_linewidths = self.linewidths[:]

            if hover_edgecolors[hovered_index] != "red":
                hover_edgecolors[hovered_index] = "black"
                hover_linewidths[hovered_index] = 2

            self.scatter.set_edgecolors(hover_edgecolors)
            self.scatter.set_linewidths(hover_linewidths)
            self.canvas.draw()
        else:
            self.tooltip.hide()
            self.scatter.set_edgecolors(self.edgecolors)
            self.scatter.set_linewidths(self.linewidths)
            self.canvas.draw()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return
        
        cont, ind = self.scatter.contains(event)

        if cont:
            clicked_index = ind["ind"][0]

            if self.edgecolors[clicked_index] == "red":
                self.edgecolors[clicked_index] = "white"
                self.linewidths[clicked_index] = 0.5
                self.selected_indices.remove(clicked_index)
            else:
                self.edgecolors[clicked_index] = "red"
                self.linewidths[clicked_index] = 2
                self.selected_indices.add(clicked_index)

            self.scatter.set_edgecolors(self.edgecolors)
            self.scatter.set_linewidths(self.linewidths)
            self.canvas.draw()

    def position_colorbar_labels(self):
        if self.cbar is None:
            return

        self.cbar.ax.set_position([0.55, 0.12, 0.4, 0.02])

        cbar_pos = self.cbar.ax.get_position()
        x_start, y_start, width, height = cbar_pos.bounds

        left_x = x_start + 0.07
        right_x = x_start + width - 0.07
        center_y = y_start + height / 2

        if self.left_label is not None and self.right_label is not None:
            self.left_label.set_position((left_x, center_y))
            self.right_label.set_position((right_x, center_y))
        else:
            self.left_label = self.figure.text(
                left_x,
                center_y,
                "Low Happiness",
                va="center",
                ha="right",
                fontsize=10,
                weight="bold",
                color="black"
            )
            self.right_label = self.figure.text(
                right_x,
                center_y,
                "High Happiness",
                va="center",
                ha="left",
                fontsize=10,
                weight="bold",
                color="black"
            )

        happiness_title_y = y_start + height + 0.03
        happiness_title_x = x_start + width / 2
        if hasattr(self, "happiness_title"):
            self.happiness_title.set_position((happiness_title_x, happiness_title_y))
        else:
            self.happiness_title = self.figure.text(
                happiness_title_x,
                happiness_title_y,
                "Happiness Score",
                fontsize=12,
                ha='center',
                va='bottom',
                weight='bold'
            )

        self.canvas.draw()

    def update_button_styles(self, selected_button):
        default_style = (
            "QPushButton {"
            "    background-color: #555555;"
            "    font-weight: bold;"
            "    border-radius: 10px;"
            "    padding: 10px 15px;"
            "    font-size: 14px;"
            "}"
        )
        highlighted_style = (
            "QPushButton {"
            "    background-color: orange;"
            "    font-weight: bold;"
            "    border-radius: 10px;"
            "    padding: 10px 15px;"
            "    font-size: 14px;"
            "}"
        )

        for button in self.buttons:
            button.setStyleSheet(default_style)

        selected_button.setStyleSheet(highlighted_style)

''' -------- Brush Class -------- '''
gray =   (0.7, 0.7, 0.7, 1.0)
class Brush:
    def __init__(self, df, ax, canvas, default_colors, size_scaled):
        self.data = df
        self.ax = ax
        self.canvas = canvas
        self.selected = []
        self.default_colors = list(default_colors)
        self.colors = list(default_colors)
        self.sizes = size_scaled
        self.scatter_plot = None
    
    def update_colors(self, selected):
        if len(selected) == 0:
            self.colors = list(self.default_colors)
        else:
            self.colors = [gray if i not in selected else self.default_colors[i] for i in range(len(self.data))]

    def callback(self, eclick, erelease, x_attr, y_attr):
        if self.scatter_plot is not None and self.scatter_plot in self.ax.collections:
            self.scatter_plot.remove()
            self.scatter_plot = None

        self.data = self.data.dropna(subset=[x_attr, y_attr]).reset_index(drop=True)
        self.data[x_attr] = pd.to_numeric(self.data[x_attr], errors='coerce')
        self.data[y_attr] = pd.to_numeric(self.data[y_attr], errors='coerce')

        x1, x2 = sorted([eclick.xdata, erelease.xdata])
        y1, y2 = sorted([eclick.ydata, erelease.ydata])

        self.selected = self.data[(self.data[x_attr].between(x1, x2, inclusive='both')) &
                                (self.data[y_attr].between(y1, y2, inclusive='both'))]
        self.update_colors(list(self.selected.index))
        self.scatter_plot = self.ax.scatter(
            self.data[x_attr],
            self.data[y_attr],
            c=self.colors,
            s=self.sizes,
            alpha=0.6,
            edgecolors='w',
            linewidths=0.5,
            antialiased=False,
        )
        self.canvas.draw()

''' -------- Brushing Chart App -------- '''
class BrushingChart(QWidget):
    def __init__(self):
        super().__init__()
        self.data = pd.read_csv("WHR2023.csv")
        self.data = self.data.dropna()

        excluded_column = 'Ladder score in Dystopia'
        self.data = self.data.loc[:, self.data.columns != excluded_column]
 
        main_layout = QGridLayout(self)

        self.tooltip_enabled = True
        self.legend_enabled_1 = True
        self.legend_enabled_2 = True

        # FIGURE ONE
        graph1_layout = QVBoxLayout()
        self.mpl_canvas_1 = FigureCanvas(Figure(figsize=(9, 7)))
        self.ax_1 = self.mpl_canvas_1.figure.subplots()

        self.x_dropdown_1 = QComboBox(self)
        self.x_dropdown_1.addItems(self.data.columns)
        self.x_dropdown_1.setFixedSize(200, 30)

        self.y_dropdown_1 = QComboBox(self)
        self.y_dropdown_1.addItems(self.data.columns)
        self.y_dropdown_1.setFixedSize(200, 30)

        self.color_dropdown_1 = QComboBox(self)
        self.color_dropdown_1.addItems(self.data.columns)
        self.color_dropdown_1.setFixedSize(200, 30)
        
        self.size_dropdown_1 = QComboBox(self)
        self.size_dropdown_1.addItems(self.data.columns)
        self.size_dropdown_1.setFixedSize(200, 30)

        self.size_slider_1 = QSlider(Qt.Orientation.Horizontal, self)
        self.size_slider_1.setRange(1, 100)
        self.size_slider_1.setValue(50)
        self.size_slider_1.valueChanged.connect(self.update_data)

        self.toggle_legend_btn_1 = QPushButton("Legend (Graph 1)", self)
        self.toggle_legend_btn_1.setIcon(QIcon("Icons/ToggleButtonOn.png"))
        self.toggle_legend_btn_1.setIconSize(QSize(40, 40))
        self.toggle_legend_btn_1.setFixedSize(150, 25)
        self.toggle_legend_btn_1.setStyleSheet("""
            QPushButton {
                border: none;
            }
        """)
        self.toggle_legend_btn_1.clicked.connect(lambda: self.toggle_legend(1))

        controls_container_1 = QVBoxLayout()
        controls_layout_1 = QGridLayout()

        controls_layout_1.addWidget(self.toggle_legend_btn_1, 0, 0, 1, 4)
        controls_layout_1.addWidget(QLabel('X Axis (Graph 1):'), 1, 0)
        controls_layout_1.addWidget(self.x_dropdown_1, 1, 1)
        controls_layout_1.addWidget(QLabel('Y Axis (Graph 1):'), 1, 2)
        controls_layout_1.addWidget(self.y_dropdown_1, 1, 3)
        controls_layout_1.addWidget(QLabel('Size (Graph 1):'), 2, 0)
        controls_layout_1.addWidget(self.size_dropdown_1, 2, 1)
        controls_layout_1.addWidget(QLabel('Color (Graph 1):'), 2, 2)
        controls_layout_1.addWidget(self.color_dropdown_1, 2, 3)
        controls_layout_1.addWidget(QLabel('Size Scale (Graph 1):'), 3, 0)
        controls_layout_1.addWidget(self.size_slider_1, 3, 1, 1, 3)

        controls_container_1.addLayout(controls_layout_1)

        graph1_layout.addWidget(NavigationToolbar(self.mpl_canvas_1, self))
        graph1_layout.addWidget(self.mpl_canvas_1)
        graph1_layout.addLayout(controls_container_1)

        # FIGURE TWO
        graph2_layout = QVBoxLayout()
        self.mpl_canvas_2 = FigureCanvas(Figure(figsize=(9, 7)))
        self.ax_2 = self.mpl_canvas_2.figure.subplots()

        self.x_dropdown_2 = QComboBox(self)
        self.x_dropdown_2.addItems(self.data.columns)
        self.x_dropdown_2.setFixedSize(200, 30)

        self.y_dropdown_2 = QComboBox(self)
        self.y_dropdown_2.addItems(self.data.columns)
        self.y_dropdown_2.setFixedSize(200, 30)

        self.color_dropdown_2 = QComboBox(self)
        self.color_dropdown_2.addItems(self.data.columns)
        self.color_dropdown_2.setFixedSize(200, 30)

        self.size_dropdown_2 = QComboBox(self)
        self.size_dropdown_2.addItems(self.data.columns)
        self.size_dropdown_2.setFixedSize(200, 30)

        self.size_slider_2 = QSlider(Qt.Orientation.Horizontal, self)
        self.size_slider_2.setRange(1, 100)
        self.size_slider_2.setValue(50)
        self.size_slider_2.valueChanged.connect(self.update_data)

        self.toggle_legend_btn_2 = QPushButton("Legend (Graph 2)", self)
        self.toggle_legend_btn_2.setIcon(QIcon("Icons/ToggleButtonOn.png"))
        self.toggle_legend_btn_2.setIconSize(QSize(40, 40))
        self.toggle_legend_btn_2.setFixedSize(150, 25)
        self.toggle_legend_btn_2.setStyleSheet("""
            QPushButton {
                border: none;
            }
        """)
        self.toggle_legend_btn_2.clicked.connect(lambda: self.toggle_legend(2))

        controls_container_2 = QVBoxLayout()
        controls_layout_2 = QGridLayout()

        controls_layout_2.addWidget(self.toggle_legend_btn_2, 0, 0, 1, 4)
        controls_layout_2.addWidget(QLabel('X Axis (Graph 2):'), 1, 0)
        controls_layout_2.addWidget(self.x_dropdown_2, 1, 1)
        controls_layout_2.addWidget(QLabel('Y Axis (Graph 2):'), 1, 2)
        controls_layout_2.addWidget(self.y_dropdown_2, 1, 3)
        controls_layout_2.addWidget(QLabel('Size (Graph 2):'), 2, 0)
        controls_layout_2.addWidget(self.size_dropdown_2, 2, 1)
        controls_layout_2.addWidget(QLabel('Color (Graph 2):'), 2, 2)
        controls_layout_2.addWidget(self.color_dropdown_2, 2, 3)
        controls_layout_2.addWidget(QLabel('Size Scale (Graph 2):'), 3, 0)
        controls_layout_2.addWidget(self.size_slider_2, 3, 1, 1, 3)

        controls_container_2.addLayout(controls_layout_2)

        graph2_layout.addWidget(NavigationToolbar(self.mpl_canvas_2, self))
        graph2_layout.addWidget(self.mpl_canvas_2)
        graph2_layout.addLayout(controls_container_2)

        # TOOLTIP
        self.toggle_tooltip_btn = QPushButton("Tooltip", self)
        self.toggle_tooltip_btn.setIcon(QIcon("Icons/ToggleButtonOn.png"))
        self.toggle_tooltip_btn.setIconSize(QSize(40, 40))
        self.toggle_tooltip_btn.setFixedSize(100, 25)
        self.toggle_tooltip_btn.setStyleSheet("""
            QPushButton {
                border: none;
            }
        """)
        self.toggle_tooltip_btn.clicked.connect(self.toggle_tooltip)

        tooltip_widget = QWidget()
        tooltip_layout = QHBoxLayout(tooltip_widget)
        tooltip_layout.setContentsMargins(0, 0, 0, 0)
        tooltip_layout.setSpacing(0)
        tooltip_layout.addWidget(self.toggle_tooltip_btn)

        # MAIN LAYOUT
        main_layout.addLayout(graph1_layout, 0, 0)             # LEFT: Graph 1
        main_layout.addLayout(graph2_layout, 0, 1)             # RIGHT: Graph 2
        main_layout.addWidget(tooltip_widget, 1, 0, 1, 2)      # BOTTOM: Tooltip button
        main_layout.setRowStretch(0, 1)

        for dropdown in [self.x_dropdown_1, self.y_dropdown_1, self.size_dropdown_1, self.color_dropdown_1]:
            dropdown.activated.connect(self.update_data)

        for dropdown in [self.x_dropdown_2, self.y_dropdown_2, self.size_dropdown_2, self.color_dropdown_2]:
            dropdown.activated.connect(self.update_data)

        self.color_bar_1 = None
        self.color_bar_2 = None

        self.brush1 = Brush(self.data, self.ax_1, self.mpl_canvas_1, [], [])
        self.brush2 = Brush(self.data, self.ax_2, self.mpl_canvas_2, [], [])

        self.selector1 = RectangleSelector(self.ax_1, lambda eclick, erelease: self.select(eclick, erelease, 1),
                                           interactive=True, button=[1], minspanx=5, minspany=5, spancoords='pixels', useblit=True)
        self.selector2 = RectangleSelector(self.ax_2, lambda eclick, erelease: self.select(eclick, erelease, 2),
                                           interactive=True, button=[1], minspanx=5, minspany=5, spancoords='pixels', useblit=True)
        
        self.tooltip = QLabel(self)
        self.tooltip.setStyleSheet("background-color: white; border-radius: 15px; padding: 5px;")
        self.tooltip.setFixedSize(400, 300)
        self.tooltip.move(50, 50)
        shadow = QGraphicsDropShadowEffect(self.tooltip)
        shadow.setBlurRadius(15)
        shadow.setOffset(5, 5)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.tooltip.setGraphicsEffect(shadow)
        self.tooltip.hide()

        self.mpl_canvas_1.mpl_connect('motion_notify_event', self.on_hover)
        self.mpl_canvas_2.mpl_connect('motion_notify_event', self.on_hover)

        self.update_data()

    def update_data(self):
        self.update_graph(self.ax_1, self.mpl_canvas_1, self.x_dropdown_1, self.y_dropdown_1,
                          self.size_dropdown_1, self.color_dropdown_1, self.size_slider_1, 1)

        self.update_graph(self.ax_2, self.mpl_canvas_2, self.x_dropdown_2, self.y_dropdown_2,
                          self.size_dropdown_2, self.color_dropdown_2, self.size_slider_2, 2)

    def update_graph(self, ax, canvas, x_dropdown, y_dropdown, size_dropdown, color_dropdown, size_slider, graph_number):
        x_attr = x_dropdown.currentText()
        y_attr = y_dropdown.currentText()
        size_attr = size_dropdown.currentText()
        color_attr = color_dropdown.currentText()
        scale_factor = size_slider.value()

        if not pd.api.types.is_numeric_dtype(self.data[color_attr]):
            self.data[color_attr] = pd.factorize(self.data[color_attr])[0]

        size_data = pd.to_numeric(self.data[size_attr], errors='coerce').fillna(1)
        size_data = size_data.clip(lower=0)

        size_scaled = self.scale(size_attr, scale_factor)

        color = pd.to_numeric(self.data[color_attr], errors='coerce')
        norm = plt.Normalize(vmin=color.min(), vmax=color.max())
        cmap = plt.get_cmap('viridis')
        default_colors = cmap(norm(color))

        if graph_number == 1:
            self.brush1 = Brush(self.data, ax, canvas, default_colors, size_scaled)
        elif graph_number == 2:
            self.brush2 = Brush(self.data, ax, canvas, default_colors, size_scaled)

        ax.clear()
        scatter = ax.scatter(
            x=self.data[x_attr],
            y=self.data[y_attr],
            s=size_scaled,
            c=self.data[color_attr],
            cmap='viridis',
            alpha=0.6,
            edgecolors='w',
            linewidths=0.5
        )
        if graph_number == 1:
            self.brush1.scatter_plot = scatter
        elif graph_number == 2:
            self.brush2.scatter_plot = scatter

        color_bar = getattr(self, f'color_bar_{graph_number}')
        if color_bar is None:
            color_bar = canvas.figure.colorbar(scatter, ax=ax, shrink=0.9)
            setattr(self, f'color_bar_{graph_number}', color_bar)
        else:
            color_bar.update_normal(scatter)
        color_bar.set_label(f'{color_attr}')

        legend_enabled = getattr(self, f'legend_enabled_{graph_number}')
        if legend_enabled:
            size_legend = add_dynamic_size_legend(ax, size_data, size_attr, scale_factor)
            ax.add_artist(size_legend)

        ax.set_xlabel(x_attr, weight='bold')
        ax.set_ylabel(y_attr, weight='bold')

        title_text = f'{x_attr}, {y_attr}, {size_attr}, {color_attr}'
        ax.set_title(wrap_title(title_text, max_len=40), weight='bold', fontsize=10)

        canvas.draw()
    
    def scale(self, size_attr, scale):
        size = pd.to_numeric(self.data[size_attr], errors='coerce')
        min_r, max_r = 50, 1000
        return min_r + ((size - size.min()) / (size.max() - size.min())) * (max_r - min_r) * scale / 50
    
    def select(self, eclick, erelease, graph):
        x_attr1, y_attr1 = self.x_dropdown_1.currentText(), self.y_dropdown_1.currentText()
        x_attr2, y_attr2 = self.x_dropdown_2.currentText(), self.y_dropdown_2.currentText()

        if graph == 1:
            self.brush1.callback(eclick, erelease, x_attr1, y_attr1)
            
            selected = self.brush1.selected.index if not self.brush1.selected.empty else []
            self.brush2.update_colors(selected)
            scale_2 = self.scale(self.size_dropdown_2.currentText(), self.size_slider_2.value())
            
            self.ax_2.scatter(self.data[x_attr2], self.data[y_attr2], s=scale_2, c=self.brush2.colors, alpha=0.6, edgecolors='w', linewidths=0.5)
            self.mpl_canvas_2.draw()
            

        if graph == 2:
            self.brush2.callback(eclick, erelease, x_attr2, y_attr2)
            
            selected = self.brush2.selected.index if not self.brush2.selected.empty else []
            self.brush1.update_colors(selected)
            scale_1 = self.scale(self.size_dropdown_1.currentText(), self.size_slider_1.value())

            self.ax_1.scatter(self.data[x_attr1], self.data[y_attr1], s=scale_1, c=self.brush1.colors, alpha=0.6, edgecolors='w', linewidths=0.5)
            self.mpl_canvas_1.draw()
    
    def on_hover(self, event):
        if not self.tooltip_enabled:
            self.tooltip.hide()
            return
        
        if event.inaxes not in [self.ax_1, self.ax_2]:
            self.tooltip.hide()
            return
        
        scatter = None
        canvas = None
        if event.inaxes == self.ax_1:
            scatter = self.brush1.scatter_plot
            canvas = self.mpl_canvas_1
        elif event.inaxes == self.ax_2:
            scatter = self.brush2.scatter_plot
            canvas = self.mpl_canvas_2

        if scatter is None:
            self.tooltip.hide()
            return

        cont, ind = scatter.contains(event)
        if cont:
            hovered_index = ind["ind"][0]

            details = f"Row Index: {hovered_index}\n"
            for column in self.data.columns:
                value = self.data.iloc[hovered_index][column]
                details += f"{column}: {value}\n"
            self.tooltip.setStyleSheet("""
                background-color: white;
                border-radius: 15px;
                padding: 10px;
                color: black;
                font-size: 12px;
            """)
            self.tooltip.setText(details)
            self.tooltip.adjustSize()
            self.tooltip.show()

            global_pos = canvas.mapToGlobal(event.guiEvent.pos())
            local_pos = self.mapFromGlobal(global_pos)

            mouse_x = local_pos.x()
            mouse_y = local_pos.y()
            tooltip_width = self.tooltip.width()
            tooltip_height = self.tooltip.height()

            offset_x = 20
            offset_y = 20

            window_geometry = self.geometry()
            window_width, window_height = (
                window_geometry.width(),
                window_geometry.height(),
            )

            if mouse_x + offset_x + tooltip_width > window_width:
                offset_x = -tooltip_width - 20
            if mouse_y + offset_y + tooltip_height > window_height:
                offset_y = -tooltip_height - 20

            if mouse_x + offset_x < 0:
                offset_x = 20
            if mouse_y + offset_y < 0:
                offset_y = 20

            new_x = mouse_x + offset_x
            new_y = mouse_y + offset_y

            self.tooltip.move(new_x + 5, new_y + 5)

            edge_colors = ["black" if i == hovered_index else "white" for i in range(len(self.data))]
            scatter.set_edgecolors(edge_colors)
            scatter.set_linewidths([2 if i == hovered_index else 0.5 for i in range(len(self.data))])

            if event.inaxes == self.ax_1:
                self.mpl_canvas_1.draw()
            elif event.inaxes == self.ax_2:
                self.mpl_canvas_2.draw()
        else:
            self.tooltip.hide()
            scatter.set_edgecolors("white")
            scatter.set_linewidths(0.5)
            if event.inaxes == self.ax_1:
                self.mpl_canvas_1.draw()
            elif event.inaxes == self.ax_2:
                self.mpl_canvas_2.draw()

    def toggle_tooltip(self):
        self.tooltip_enabled = not self.tooltip_enabled
        if self.tooltip_enabled:
            self.toggle_tooltip_btn.setText("Tooltip")
            self.toggle_tooltip_btn.setIcon(QIcon("Icons/ToggleButtonOn.png"))
        else:
            self.toggle_tooltip_btn.setText("Tooltip")
            self.toggle_tooltip_btn.setIcon(QIcon("Icons/ToggleButtonOff.png"))
    
    def toggle_legend(self, graph_number):
        if graph_number == 1:
            self.legend_enabled_1 = not self.legend_enabled_1
            if self.legend_enabled_1:
                size_attr = self.size_dropdown_1.currentText()
                scale_factor = self.size_slider_1.value()
                size_data = pd.to_numeric(self.data[size_attr], errors='coerce').fillna(1).clip(lower=0)
                size_legend = add_dynamic_size_legend(self.ax_1, size_data, size_attr, scale_factor)
                self.ax_1.add_artist(size_legend)
                self.toggle_legend_btn_1.setIcon(QIcon("Icons/ToggleButtonOn.png"))
            else:
                legend = self.ax_1.get_legend()
                if legend is not None:
                    legend.set_visible(False)
                    self.toggle_legend_btn_1.setIcon(QIcon("Icons/ToggleButtonOff.png"))
            self.mpl_canvas_1.draw()
        elif graph_number == 2:
            self.legend_enabled_2 = not self.legend_enabled_2
            if self.legend_enabled_2:
                size_attr = self.size_dropdown_2.currentText()
                scale_factor = self.size_slider_2.value()
                size_data = pd.to_numeric(self.data[size_attr], errors='coerce').fillna(1).clip(lower=0)
                size_legend = add_dynamic_size_legend(self.ax_2, size_data, size_attr, scale_factor)
                self.ax_2.add_artist(size_legend)
                self.toggle_legend_btn_2.setIcon(QIcon("Icons/ToggleButtonOn.png"))
            else:
                legend = self.ax_2.get_legend()
                if legend is not None:
                    legend.set_visible(False)
                    self.toggle_legend_btn_2.setIcon(QIcon("Icons/ToggleButtonOff.png"))
            self.mpl_canvas_2.draw()

''' -------- Map Chart App -------- '''
class MapChart(QWidget):
    def __init__(self):
        super().__init__()

        self.is_zooming = False
        self.highlight_patch = None
        self.visible_labels = []

        self.worldmap = gpd.read_file("world_map.json", driver='GeoJSON')

        self.data = pd.read_csv("WHR2023.csv")    
        country_to_code = {country.name: country.alpha_3 for country in pycountry.countries}
        
        self.data['Country code'] = self.data['Country name'].map(country_to_code)

        manual_mapping = {
            "Taiwan Province of China": "TWN",
            "Kosovo": "XKX",
            "South Korea": "KOR",
            "Moldova": "MDA",
            "Vietnam": "VNM",
            "Bolivia": "BOL",
            "Russia": "RUS",
            "Hong Kong S.A.R. of China": "HKG",
            "Congo (Brazzaville)": "COG",
            "Congo (Kinshasa)": "COD",
            "Venezuela": "VEN",
            "Laos": "LAO",
            "Ivory Coast": "CIV",
            "State of Palestine": "PSE",
            "Iran": "IRN",
            "Turkiye": "TUR",
            "Tanzania": "TZA",
        }
        self.data['Country code'] = self.data['Country code'].fillna(self.data['Country name'].map(manual_mapping))

        # Map ladder score to worldmap using ISO codes
        country_happiness = dict(zip(self.data['Country code'], self.data['Ladder score']))
        self.worldmap['Ladder score'] = self.worldmap['adm0_a3'].map(country_happiness)

        color = pd.to_numeric(self.data["Ladder score"], errors='coerce')
        norm = plt.Normalize(vmin=color.min(), vmax=color.max())
        colormap = plt.get_cmap('viridis')

        self.worldmap['color'] = self.worldmap['Ladder score'].apply(
            lambda x: colormap(norm(x)) if pd.notna(x) else (0.8, 0.8, 0.8, 1)
        )

        self.figure, self.ax = plt.subplots(figsize=(15, 8))
        self.canvas = FigureCanvas(self.figure)

        self.plot_map()

        self.tooltip = QLabel(self)
        self.tooltip.setStyleSheet("background-color: white; border-radius: 15px; padding: 5px;")
        self.tooltip.move(50, 50)
        shadow = QGraphicsDropShadowEffect(self.tooltip)
        shadow.setBlurRadius(15)
        shadow.setOffset(5, 5)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.tooltip.setGraphicsEffect(shadow)
        self.tooltip.hide()

        self.canvas.mpl_connect("motion_notify_event", self.on_hover)
        self.canvas.mpl_connect('button_release_event', self.on_zoom)

        layout = QVBoxLayout()
        layout.addWidget(NavigationToolbar(self.canvas, self))
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot_map(self):
        self.worldmap.plot(
            ax=self.ax,
            color=self.worldmap["color"],
            edgecolor='black',
            linewidth=1,
        )

        norm = plt.Normalize(vmin=self.worldmap['Ladder score'].min(), vmax=self.worldmap['Ladder score'].max())
        colormap = plt.get_cmap('viridis')
        sm = plt.cm.ScalarMappable(cmap=colormap, norm=norm)
        sm.set_array([])

        cbar = self.figure.colorbar(sm, ax=self.ax, orientation='vertical', fraction=0.025, pad=0.01)
        cbar.set_label("Happiness Score", fontsize=12, fontweight='bold')

        self.ax.axis('off')
        self.ax.set_frame_on(False)
        self.ax.margins(0)
        self.figure.tight_layout()

        self.plot_labels()

    def plot_labels(self):
        for idx, row in self.worldmap.iterrows():
            if pd.notna(row["Ladder score"]) and row['geometry'] is not None:
                if row['geometry'].geom_type == "Polygon":
                    point = row['geometry'].representative_point()
                elif row['geometry'].geom_type == "MultiPolygon":
                    largest_polygon = max(row['geometry'].geoms, key=lambda p: p.area)
                    point = largest_polygon.representative_point()
                else:
                    continue

                label_text = f"{row['Ladder score']:.1f}"
                text = self.ax.text(
                    point.x, point.y, label_text,
                    fontsize=8, ha='center', va='center', color='black', weight='bold',
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0, visible=False)
                )
                self.visible_labels.append((text, row['geometry']))
        self.update_labels()
    
    def on_zoom(self, event):
        if self.ax.get_navigate_mode() == 'ZOOM':
            self.is_zooming = False
            self.update_labels()
            self.canvas.draw_idle()
            
    def update_labels(self):
        xlim, ylim = self.ax.get_xlim(), self.ax.get_ylim()
        visible_area = shapely.geometry.box(xlim[0], ylim[0], xlim[1], ylim[1])

        for text, geometry in self.visible_labels:
            if geometry.geom_type == "Polygon":
                representative_point = geometry.representative_point()
            elif geometry.geom_type == "MultiPolygon":
                largest_polygon = max(geometry.geoms, key=lambda p: p.area)
                representative_point = largest_polygon.representative_point()
            else:
                text.set_visible(False)
                continue

            point_in_visible_area = visible_area.contains(representative_point)
            country_area = geometry.area
            label_visible = point_in_visible_area and country_area > visible_area.area * 0.0015
            text.set_visible(label_visible)

    def on_hover(self, event):
        if self.ax.get_navigate_mode() == "ZOOM":
            self.is_zooming = True

        if event.inaxes != self.ax:
            self.tooltip.hide()
            self.remove_highlight()
            return
        
        hover_point = shapely.geometry.Point(event.xdata, event.ydata)

        for idx, row in self.worldmap.iterrows():
            if row['geometry'].contains(hover_point):
                country_name = row.get("name", "Unknown Country")
                ladder_score = row.get("Ladder score", "No Data")
                data_row = self.data[self.data['Country code'] == row['adm0_a3']].iloc[0] if not self.data[self.data['Country code'] == row['adm0_a3']].empty else None
                if data_row is not None:
                    details = (
                        f"<b>{data_row['Country name']}</b><br>"
                        f"Ladder Score: {data_row['Ladder score']:.2f}<br>"
                        f"Standard Error: {data_row['Standard error of ladder score']:.2f}<br>"
                        f"Upperwhisker: {data_row['upperwhisker']:.2f}<br>"
                        f"Lowerwhisker: {data_row['lowerwhisker']:.2f}<br>"
                        f"Logged GDP per Capita: {data_row['Logged GDP per capita']:.2f}<br>"
                        f"Social Support: {data_row['Social support']:.2f}<br>"
                        f"Healthy Life Expectancy: {data_row['Healthy life expectancy']:.2f}<br>"
                        f"Freedom to Make Life Choices: {data_row['Freedom to make life choices']:.2f}<br>"
                        f"Generosity: {data_row['Generosity']:.2f}<br>"
                        f"Perceptions of Corruption: {data_row['Perceptions of corruption']:.2f}<br>"
                        f"Explained by Log GDP per Capita: {data_row['Explained by: Log GDP per capita']:.2f}<br>"
                        f"Explained by Social Support: {data_row['Explained by: Social support']:.2f}<br>"
                        f"Explained by Healthy Life Expectancy: {data_row['Explained by: Healthy life expectancy']:.2f}<br>"
                        f"Explained by Freedom to Make Life Choices: {data_row['Explained by: Freedom to make life choices']:.2f}"
                    )
                    self.tooltip.setFixedSize(375, 315)
                else:
                    details = f"<b>{country_name}</b><br>Happiness Score: {ladder_score}"
                    self.tooltip.setFixedSize(220, 60)
                self.tooltip.setStyleSheet("""
                    background-color: white;
                    border-radius: 15px;
                    padding: 10px;
                    color: black;
                    font-size: 16px;
                """)
                self.tooltip.setText(details)
                self.tooltip.adjustSize()
                self.tooltip.raise_()
                self.tooltip.show()

                global_pos = self.canvas.mapToGlobal(event.guiEvent.pos())
                local_pos = self.mapFromGlobal(global_pos)

                mouse_x = local_pos.x()
                mouse_y = local_pos.y()
                tooltip_width = self.tooltip.width()
                tooltip_height = self.tooltip.height()

                offset_x = 20
                offset_y = 20

                window_geometry = self.geometry()
                window_width, window_height = (
                    window_geometry.width(),
                    window_geometry.height(),
                )

                if mouse_x + offset_x + tooltip_width > window_width:
                    offset_x = -tooltip_width - 20
                if mouse_y + offset_y + tooltip_height > window_height:
                    offset_y = -tooltip_height - 20

                if mouse_x + offset_x < 0:
                    offset_x = 20
                if mouse_y + offset_y < 0:
                    offset_y = 20

                new_x = mouse_x + offset_x
                new_y = mouse_y + offset_y

                self.tooltip.move(new_x + 5, new_y + 5)

                self.highlight_country(row['geometry'])
                self.canvas.draw()
                break
        else:
            self.tooltip.hide()
            self.remove_highlight()
            self.canvas.draw()

    def highlight_country(self, geometry):
        if self.highlight_patch:
            self.remove_highlight()

        patches = []

        if geometry.geom_type == "Polygon":
            patches.append(Polygon(geometry.exterior.coords, linewidth=2, edgecolor="red", facecolor="none"))
        elif geometry.geom_type == "MultiPolygon":
            for poly in geometry.geoms:
                patches.append(Polygon(poly.exterior.coords, linewidth=2, edgecolor="red", facecolor="none"))
        else:
            return
        
        self.highlight_patch = PatchCollection(patches, match_original=True)
        self.ax.add_collection(self.highlight_patch)

    def remove_highlight(self):
        if self.highlight_patch:
            self.highlight_patch.remove()
            self.highlight_patch = None

class MainApp(QMainWindow):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.showNormal()
            self.resize(1000, 1400) 

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Toggle Visualization App")
        self.resize(1200, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        button_layout = QHBoxLayout()
        self.bubble_button = QPushButton("Bubble Chart")
        self.brushing_button = QPushButton("Brushing Chart")
        self.map_button = QPushButton("Map View")

        button_style = (
            "QPushButton {"
            "   background-color: lightgray;"
            "   border-radius: 15px;"
            "   padding: 10px 20px;"
            "   height: 30px;"
            "   font-size: 14px;"
            "}"
        )
        self.bubble_button.setStyleSheet(button_style)
        self.brushing_button.setStyleSheet(button_style)
        self.map_button.setStyleSheet(button_style)

        self.bubble_button.clicked.connect(lambda: self.switch_view(0))
        self.brushing_button.clicked.connect(lambda: self.switch_view(1))
        self.map_button.clicked.connect(lambda: self.switch_view(2))

        button_layout.addWidget(self.bubble_button)
        button_layout.addWidget(self.brushing_button)
        button_layout.addWidget(self.map_button)
        layout.addLayout(button_layout)

        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

        self.bubble_chart = BubbleChart()
        self.brushing_chart = BrushingChart()
        self.map_chart = MapChart()

        self.stacked_widget.addWidget(self.bubble_chart)
        self.stacked_widget.addWidget(self.brushing_chart)
        self.stacked_widget.addWidget(self.map_chart)

        self.stacked_widget.setCurrentIndex(0)
        self.update_button_styles()

    def switch_view(self, index):
        self.stacked_widget.setCurrentIndex(index)
        self.update_button_styles()
    
    def update_button_styles(self):
        default_style = (
            "QPushButton {"
            "    background-color: #555555;"
            "    font-weight: bold;"
            "    border-radius: 15px;"
            "    padding: 10px 20px;"
            "    height: 30px;"
            "   font-size: 14px;"
            "}"
        )
        selected_style = (
            "QPushButton {"
            "    background-color: orange;"
            "    font-weight: bold;"
            "    border-radius: 15px;"
            "    padding: 10px 20px;"
            "    height: 30px;"
            "   font-size: 14px;"
            "}"
        )

        self.bubble_button.setStyleSheet(default_style)
        self.brushing_button.setStyleSheet(default_style)
        self.map_button.setStyleSheet(default_style)

        current_index = self.stacked_widget.currentIndex()
        if current_index == 0:
            self.bubble_button.setStyleSheet(selected_style)
        elif current_index == 1:
            self.brushing_button.setStyleSheet(selected_style)
        elif current_index == 2:
            self.map_button.setStyleSheet(selected_style)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()

    window.showFullScreen()

    window.activateWindow()
    window.raise_()

    sys.exit(app.exec())