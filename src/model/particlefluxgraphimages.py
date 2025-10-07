import csv
import cv2
import datetime as dt
import io
import json
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import os
import sys

from datetime import datetime
from PIL import Image

from common.constants import UPDATE_PERCENTAGE
from common.exceptions import NoDataFoundError


class ParticleFluxGraphImages():

    ## CONSTRUCTOR --------------------------------------------------------------------------------------------------------- ##
    ## It that will directly build the graph images
    def __init__(self, beginDateTime : datetime, endDateTime : datetime, dctEnergy : dict[str, bool], imageWidth : float, imageHeight : float, inputFolder : str, numberOfImages = None, loadingFrameQueue = None):
        
        # Defining attributes from parameters
        self.beginDateTime = beginDateTime
        self.endDateTime = endDateTime
        self.dctEnergy = dctEnergy
        self.imageWidth = imageWidth
        self.imageHeight = imageHeight
        self.inputFolder = inputFolder
        self.numberOfImages = numberOfImages
        self.loadingFrameQueue = loadingFrameQueue

        # Defining dictionaries for particle flux
        proton_flux_dictionary = None
        neutron_flux_dictionary = None
        
        # Getting Proton flux data dictionary if selected
        if dctEnergy["ProtonFlux"]:
            proton_flux_dictionary = self.proton_json_to_dict(self.beginDateTime, self.endDateTime, self.dctEnergy["Energies"])

        # Getting Neutron flux data dictionary if selected
        if dctEnergy["NeutronFlux"]:
            neutron_flux_dictionary = self.neutron_csv_to_dict(self.beginDateTime, self.endDateTime)

        # Generating graph images and storing them into a BytesIO tab
        self.images = self.dict_to_graph(proton_flux_dict=proton_flux_dictionary, neutron_flux_dict=neutron_flux_dictionary, image_width=self.imageWidth, image_height=self.imageHeight)
    ## --------------------------------------------------------------------------------------------------------------------- ##
    


    ## FUNCTIONS ----------------------------------------------------------------------------------------------------------- ##

    # Function to convert GOES Proton Flux data file in JSON into a legible dictionary for the graph video algorithm
    # Dictionary format : {">=1 MeV" : {timestamp1 : flux, timestamp2 : flux, ...}, ">=10 MeV" : {timestamp1 : flux, timestamp2 : flux, ...}, ...}
    def proton_json_to_dict(self, begin_date_time : datetime, end_date_time : datetime, energy_dict : dict) -> dict:
        
        # Creating a dictionary that will store the proton flux data
        final_dict = dict()
        
        # Saving previous working directory
        previous_working_directory = os.getcwd()
        
        # Setting working directory to input folder
        os.chdir(self.inputFolder)


        ## ----- Checking every data file day per day ----- ##

        current_date_time = begin_date_time # Initializing current datetime
        while current_date_time <= end_date_time:
            
            # Importing year, month and day from current_date_time
            year = current_date_time.strftime('%Y')
            month = current_date_time.strftime('%m')
            day = current_date_time.strftime('%d')
        

            # Opening file
            json_file = open(f"{year}{month}{day}_integral-protons-1-day.json")

            # Loading data as a dictionary
            json_data = json.load(json_file)

            # Checking every measure in the json file
            for measure in json_data:

                # Getting current measure's energy
                # corresponding to the measure's flux
                current_energy = measure["energy"]

                # We add this measure if only the current energy was
                # selected on the user's request
                if energy_dict[current_energy] == True:
                    
                    # Adding current_energy key if it isn't set yet
                    if current_energy not in final_dict.keys():
                        final_dict[current_energy] = dict()

                    # Getting measure["time_tag"] property into a Python datetime format
                    current_measure_datetime = datetime.strptime(measure["time_tag"], '%Y-%m-%dT%H:%M:%SZ')

                    # We add this measure to the final dictionary if only the current_measure_datetime
                    # is between begin_date_time and end_date_time
                    if current_measure_datetime >= begin_date_time and current_measure_datetime <= end_date_time:

                        # Getting current measure's flux
                        current_flux = measure["flux"]

                        # Adding this measure to the final dictionary
                        final_dict[current_energy][current_measure_datetime] = current_flux
                    

            # Incrementing current_date_time by one day
            current_date_time += dt.timedelta(days=1)
        
        ## ------------------------------------------------ ##

        # Resetting working directory to the previous one
        os.chdir(previous_working_directory)
        
        return final_dict



    # Function to convert NEST Neutron Flux data file in CSV into a legible dictionary for the graph video algorithm
    # Dictionary format : {"start_date_time" : [list of datetimes], "Measure" : [List of measures]}
    # Multiple stations version : {"start_date_time" : [list of datetimes], "KERG Measure" : [List of measures], "TERA Measure" : [List of measures]}
    def neutron_csv_to_dict(self, begin_date_time : datetime, end_date_time : datetime) -> dict:
        
        # Creating a dictionary that will store the neutron flux data
        final_dict = dict()
        
        # Saving previous working directory
        previous_working_directory = os.getcwd()
        
        # Setting working directory to input folder
        os.chdir(self.inputFolder)


        ## ----- Checking every data file day per day ----- ##

        current_date_time = begin_date_time # Initializing current datetime
        while current_date_time <= end_date_time:
            
            # Importing year, month and day from current_date_time
            year = current_date_time.strftime('%Y')
            month = current_date_time.strftime('%m')
            day = current_date_time.strftime('%d')
        

            # Building the filename
            filename = f"neutron_flux_{year}_{month}_{day}.csv"


            ## --- Changing header line --- ##
            
            # Opening the file and importing data
            with open(filename, mode="r") as csv_file:
            
                # Importing file content in a list form
                file_content = csv_file.readlines()

                # Defining header string for the first line
                header="start_date_time"

                # Case when only one sensor is set on the file
                if ("RCORR_E" in file_content[0] or "; Neutron flux" in file_content[0]):
                    header = header + "; Neutron flux"
                
                # Other cases when there are many other sensors
                else:
                    # Adding KERG and TERA on the header if they exist
                    if ("KERG" in file_content[0]):
                        header = header + "; KERG Neutron flux"
                    if ("TERA" in file_content[0]):
                        header = header + "; TERA Neutron flux"
                
                # Adding line break
                header = header + "\n"
                
                # Setting the first line of the file to the content of header
                file_content[0] = header

            # Writing new content
            with open(filename, mode="w") as csv_file:
                csv_file.writelines(file_content)
            ## ---------------------------- ##


            ## --- Converting CSV file into dictionary --- ##

            # Opening and reading CSV file
            with open(filename, mode="r") as csv_file:    
                csv_content = csv.DictReader(csv_file, delimiter=";")

                # For every line of the CSV file 
                for current_line in csv_content:
                    
                    # Converting datetimes into Python datetime format
                    reconverted_datetime = datetime.strptime(current_line["start_date_time"], '%Y-%m-%d %H:%M:%S')
                    current_line["start_date_time"] = reconverted_datetime

                    # We allow the current line to be added only if the start_date_time
                    # is between begin_date_time and end_date_time
                    if current_line["start_date_time"] >= begin_date_time and current_line["start_date_time"] <= end_date_time:

                        # For every key in the current line dictionary
                        for current_key in current_line.keys():

                            # Setting final_dict's tabs on its values
                            # if they are not already set
                            if not current_key in final_dict.keys():
                                final_dict[current_key] = []

                            # Converting neutron flux data in float (if current_key contains "Neutron Flux")
                            if "Neutron flux" in current_key:
                                final_dict[current_key].append(float(current_line[current_key]))
                            else:
                                final_dict[current_key].append(current_line[current_key])

            ## ------------------------------------------- ##

            # We increment the current_date_time by one day
            current_date_time += dt.timedelta(days=1)
        ## ------------------------------------------------ ##

        # Resetting working directory to the previous one
        os.chdir(previous_working_directory)

        return final_dict
    
    
    # Function that produces images of an animated graph, depending on Proton flux and/or Neutron flux
    def dict_to_graph(self, proton_flux_dict = None, neutron_flux_dict = None, image_width = 640, image_height = 480) -> list:

        # Building images list
        images_list = []
        
        ## ----- Setting graph boundaries ----- ##

        # Building dictionaries for boundaries
        proton_bounds = {
            'min_time': None,
            'max_time': None,
            'min_data': sys.float_info.max,
            'max_data': sys.float_info.min
        }

        neutron_bounds = {
            'min_time': None,
            'max_time': None,
            'min_data': sys.float_info.max,
            'max_data': sys.float_info.min
        }

        # Proton flux
        proton_start_datetimes = []

        if proton_flux_dict is not None:

            # The keys from the fisrt value's dictionary is enough to gather every datetimes
            first_key = list(proton_flux_dict.keys())[0]
            proton_start_datetimes = list(proton_flux_dict[first_key].keys())

            # Setting min and max times
            proton_bounds['min_time'] = min(proton_start_datetimes)
            proton_bounds['max_time'] = max(proton_start_datetimes)
            
            # Getting the min and max of all flux,
            # no matter the energy is
            for one_key in proton_flux_dict.keys():
                proton_bounds['min_data'] = min(proton_bounds['min_data'], min(proton_flux_dict[one_key].values()))
                proton_bounds['max_data'] = max(proton_bounds['max_data'], max(proton_flux_dict[one_key].values()))

        # Neutron flux
        neutron_start_datetimes = []

        if neutron_flux_dict is not None:
            neutron_start_datetimes = neutron_flux_dict["start_date_time"]

            # Setting min and max times
            neutron_bounds['min_time'] = min(neutron_start_datetimes)
            neutron_bounds['max_time'] = max(neutron_start_datetimes)
        
            # Getting the min and max of all flux,
            # no matter the measure station is
            for one_key in neutron_flux_dict.keys():

                # We ignore the "start_date_time" key,
                # because it is not a measure station
                if one_key != "start_date_time":

                    neutron_bounds['min_data'] = min(neutron_bounds['min_data'], min(neutron_flux_dict[one_key]))
                    neutron_bounds['max_data'] = max(neutron_bounds['max_data'], max(neutron_flux_dict[one_key]))

        ## -------------------------------- ##

        ## ----- Generating graph images ----- ##

        ## Determining how many images can be produced 
        # If it has been already set while constructing the whole object, we keep it
        # Otherwise, we will define the number of images depending on the minimum number of datetimes on the graph
        number_of_images = self.numberOfImages
        
        # Case when the number of images is none,
        # and has to be defined
        if number_of_images is None:

            # Case when only the proton graph is selected
            if len(proton_start_datetimes) != 0 and len(neutron_start_datetimes) == 0:
                number_of_images = len(proton_start_datetimes)

            # Case when only the neutron graph is selected
            elif len(neutron_start_datetimes) != 0 and len(proton_start_datetimes) == 0:
                number_of_images = len(neutron_start_datetimes)  

            # Case when both are selected, 
            # we pick the minimum number of datetimes
            else:
                number_of_images = min(len(proton_start_datetimes), len(neutron_start_datetimes))

        # For debug
        print("Number of graph images :", number_of_images)

        # Every line_index corresponds to a frame of the graph animation
        for line_index in range(1, number_of_images+1):

            # --- Building figure algorithm --- #
            
            # Defining plot limits for the current frame, for both graphs
            proton_plot_limit = round((len(proton_start_datetimes)*line_index)/number_of_images)
            neutron_plot_limit = round((len(neutron_start_datetimes)*line_index)/number_of_images)

            # Case for two graphs:
            if proton_flux_dict is not None and neutron_flux_dict is not None:

                # Building subplots
                fig, axs = plt.subplots(nrows=2, layout='constrained', figsize=(image_width/100, image_height/100))

                # Proton Flux
                ax = axs[0] # Importing first subplot
                generate_proton_subplot(ax, proton_flux_dict, proton_start_datetimes, proton_bounds, proton_plot_limit)

                # Neutron Flux
                ax = axs[1] # Importing second subplot
                generate_neutron_subplot(ax, neutron_flux_dict, neutron_start_datetimes, neutron_bounds, neutron_plot_limit)

                # Adding credits
                fig.suptitle('© NOAA Space Weather Prediction Center, NMDB', ha = 'left', fontsize=12)
                
                # Closing plot
                plt.close()

                # --- Saving images --- #
                current_plot_byte = io.BytesIO()
                fig.savefig(current_plot_byte, format='png') 
                current_plot_byte.seek(0) # Setting "reading cursor" at the beginning

                # We store this frame of the graph on the final images list
                images_list.append(current_plot_byte)
                # --------------------- #

            # Case for one graph:
            else:

                # Building subplot
                fig, ax = plt.subplots(figsize=(image_width/100, image_height/100))

                # Setting credits text
                credit_text = ""

                # Proton flux
                if proton_flux_dict is not None:
                    generate_proton_subplot(ax, proton_flux_dict, proton_start_datetimes, proton_bounds, proton_plot_limit)
                    credit_text = "© NOAA Space Weather Prediction Center"

                # Neutron flux
                elif neutron_flux_dict is not None:
                    generate_neutron_subplot(ax, neutron_flux_dict, neutron_start_datetimes, neutron_bounds, neutron_plot_limit)
                    credit_text = "© NMDB"

                # Closing plot
                plt.close()

                # --- Saving images --- #
                current_plot_byte = io.BytesIO()
                fig.savefig(current_plot_byte, format='png')

                current_plot_byte.seek(0) # Setting "reading cursor" at the beginning

                # We store this frame of the graph on the final images list
                images_list.append(current_plot_byte)
                # --------------------- #

            # --------------------------------- #

            # --- Increasing percentage on loading frame --- #
            self.loadingFrameQueue.put((UPDATE_PERCENTAGE, {
                "current_step": line_index,
                "total_steps": number_of_images
            }))
            # ---------------------------------------------- #

        ## ----------------------------------- #
        return images_list    

        
    ## --------------------------------------------------------------------------------------------------------------------- ##

## ---------- STATIC FUNCTIONS ---------- ##

# Function to generate a proton subplot, taking into account come parameters,
# such as the proton flux data dictionary, the start datetimes, the boundaries, and the plot index limit
def generate_proton_subplot(ax, proton_flux_dict : dict, start_datetimes : list, boundaries_dict : dict, plot_index_limit : int):
    
    
    # Setting plot boundaries
    ax.set_xlim(boundaries_dict["min_time"] - dt.timedelta(minutes=1) , boundaries_dict["max_time"] + dt.timedelta(minutes=1)) # Time on X (We add/subtract one minute as a padding)
    ax.set_ylim(boundaries_dict["min_data"], boundaries_dict["max_data"]) # Proton flux data on Y

    # Generating plot for every energy on proton_flux_dict
    for one_energy in proton_flux_dict.keys():
        
        # Setting plot limit depending on the line_index
        # and the number of images
        
        ax.plot(start_datetimes[:plot_index_limit], list(proton_flux_dict[one_energy].values())[:plot_index_limit], label=one_energy)
        ax.legend() # Enabling legends

    # Setting plot title
    ax.set_title(f"Proton flux from {format_datetime(boundaries_dict['min_time'])} to {format_datetime(boundaries_dict['max_time'])}")

    # Setting plot axis labels
    ax.set_ylabel(r'Particles∙cm$^-2$∙s$^-1$∙sr$^-1$')

    # Setting times in correct format
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax.xaxis.set_minor_locator(mdates.HourLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))

    # Enabling grid on the graph
    ax.grid(True)

    # Rotates and right-aligns the x labels so they don't crowd each other.
    for label in ax.get_xticklabels(which='major'):
        label.set(rotation=30, horizontalalignment='right')


# Function to generate a neutron subplot, taking into account come parameters,
# such as the neutron flux data dictionary, the start datetimes, the boundaries, and the plot index limit
def generate_neutron_subplot(ax, neutron_flux_dict : dict, start_datetimes : list, boundaries_dict : dict, plot_index_limit : int):
    
    
    # Setting plot boundaries
    ax.set_xlim(boundaries_dict["min_time"] - dt.timedelta(minutes=1) , boundaries_dict["max_time"] + dt.timedelta(minutes=1)) # Time on X (We add/subtract one minute as a padding)
    ax.set_ylim(boundaries_dict["min_data"], boundaries_dict["max_data"]) # Neutron flux data on Y

    # Generating plot for every station in graph_dictionary
    for one_key in neutron_flux_dict.keys():

        # We skip "start_date_time"
        if one_key != "start_date_time":
        
            # Setting plot limit depending on the line_index
            # and the number of images
            ax.plot(start_datetimes[:plot_index_limit], neutron_flux_dict[one_key][:plot_index_limit], label=one_key)
            ax.legend() # Enabling legends

    # Setting plot title
    ax.set_title(f"Neutron flux from {format_datetime(boundaries_dict['min_time'])} to {format_datetime(boundaries_dict['max_time'])}")
    
    # Setting plot axis labels
    ax.set_ylabel(r'Particles∙cm$^-2$∙s$^-1$∙sr$^-1$')

    # Setting times in correct format
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax.xaxis.set_minor_locator(mdates.HourLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))

    # Enabling grid on the graph
    ax.grid(True)

    # Rotates and right-aligns the x labels so they don't crowd each other.
    for label in ax.get_xticklabels(which='major'):
        label.set(rotation=30, horizontalalignment='right')

# Function to format the date into a legible format (Generated by ChatGPT)
def format_datetime(dt : datetime):
    suffix = 'th' if 11 <= dt.day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(dt.day % 10, 'th')
    return dt.strftime(f"%B {dt.day}{suffix} %Y at %H:%M")


## ---------- TEST ZONE ---------- ##

# ----- Video generation algorithm ----- #
def generate_video(frame_list, video_name):

    # Changing working directory to the output folder
    os.chdir('output')

    # Configuring video writer
    output_video = cv2.VideoWriter(video_name, cv2.VideoWriter_fourcc(*'mp4v'), 25, (1280, 720))

    counter = 1
    for one_frame in frame_list:

        # Saving plot as a PIL image
        current_plot_pil = Image.open(one_frame)
        
        # Converting PIL image to OpenCV format
        current_plot_cv = np.array(current_plot_pil)
        current_plot_cv = cv2.cvtColor(current_plot_cv, cv2.COLOR_RGB2BGR) # Configuring color

        # Adding frame on the video
        output_video.write(current_plot_cv)

        # For debug
        print(f'Image {counter} written')
        counter += 1

    # Exporting video
    cv2.destroyAllWindows()
    output_video.release()
    print("Video findable on " + os.getcwd() + "/" + video_name)
    os.chdir('../')
# -------------------------------------- #


# # --- Test 1 : Neutron Flux --- #
# begin_date_time = datetime(2024, 6, 17, 5, 0)
# end_date_time = datetime(2024, 6, 18, 17, 00)
# dct_energy = {"ProtonFlux" : False, "Energies" : {">=10 MeV" : True, ">=50 MeV" : True, ">=100 MeV" : True,">=500 MeV" : True, ">=1 MeV" : False, ">=30 MeV" : False, ">=5 MeV" : False, ">=60 MeV" : False, },"NeutronFlux" : True}

# # Building a test object
# test_object_1 = ParticleFluxGraphImages(beginDateTime=begin_date_time, endDateTime=end_date_time, dctEnergy=dct_energy, imageWidth=1280, imageHeight=720)

# # For debug
# print("test_object 1 created")

# # Generating test 1 
# generate_video(test_object_1.images, "solar_activid_test_neutron_flux.mp4")

# # Deleting test object
# del test_object_1
# # ----------------------------- #

# # --- Test 2 : Proton Flux --- #
# begin_date_time = datetime(2024, 4, 20, 5, 0)
# end_date_time = datetime(2024, 5, 18, 0, 0)
# dct_energy = {"ProtonFlux" : True, "Energies" : {">=10 MeV" : True, ">=50 MeV" : True, ">=100 MeV" : True,">=500 MeV" : True, ">=1 MeV" : False, ">=30 MeV" : False, ">=5 MeV" : False, ">=60 MeV" : False, },"NeutronFlux" : False}

# # Building a test object
# test_object_2 = ParticleFluxGraphImages(beginDateTime=begin_date_time, endDateTime=end_date_time, dctEnergy=dct_energy, imageWidth=1280, imageHeight=720)

# # For debug
# print("test_object 2 created")

# # Generating test 2 
# generate_video(test_object_2.images, "solar_activid_test_proton_flux.mp4")

# # Deleting test object
# del test_object_2
# # ----------------------------- #

# # --- Test 3 : Proton and Neutron Flux --- #
# begin_date_time = datetime(2024, 5, 17, 5, 0)
# end_date_time = datetime(2024, 5, 18, 0, 0)
# dct_energy = {"ProtonFlux" : True, "Energies" : {">=10 MeV" : False, ">=50 MeV" : False, ">=100 MeV" : True,">=500 MeV" : False, ">=1 MeV" : False, ">=30 MeV" : False, ">=5 MeV" : False, ">=60 MeV" : False, },"NeutronFlux" : True}

# # Building a test object
# test_object_3 = ParticleFluxGraphImages(beginDateTime=begin_date_time, endDateTime=end_date_time, dctEnergy=dct_energy, imageWidth=1280, imageHeight=720)

# # For debug
# print("test_object 3 created")

# # Generating test 3 
# generate_video(test_object_3.images, "solar_activid_test_all_flux.mp4")

# # Deleting test object
# del test_object_3
# # ----------------------------- #

# # --- Test 4 : Unreachable data --- #
# begin_date_time = datetime(2024, 5, 2, 5, 0)
# end_date_time = datetime(2024, 5, 3, 0, 0)
# dct_energy = {"ProtonFlux" : True, "Energies" : {">=10 MeV" : False, ">=50 MeV" : False, ">=100 MeV" : True,">=500 MeV" : False, ">=1 MeV" : False, ">=30 MeV" : False, ">=5 MeV" : False, ">=60 MeV" : False, },"NeutronFlux" : True}

# test_object_4 = ParticleFluxGraphImages(beginDateTime=begin_date_time, endDateTime=end_date_time, dctEnergy=dct_energy, imageWidth=1280, imageHeight=720)