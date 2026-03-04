import os
import glob
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

def load(file_path)->pd.DataFrame :
    """
    we will skip the meta data and focus on string manupilations nd extracting the signals here
    #Arguments
    - file_path: object of <class 'pathlib.PosixPath'> for the path
    #Return 
    - pd.Dataframe that contains out data
    """
    with open(file_path) as file:
        lines=file.readlines();
    
    # directly calling the even loader fucntion since i dont want to invoke methods one by one for every file it will be more better to have it on one function
    if "Flow Events" in os.path.basename(file_path):
        return load_events(lines);

    # skipping the meta data right after 'Data:'
    pos=0;
    for idx,l in enumerate(lines):
        if(l.strip()=='Data:'):
            pos=idx;break;
    
    records=[]
    #  splitting till we do not find ';' (end of ther records)
    for line in lines[pos+1:]:
        if (";" not in line):
            continue
        timestamp, value = line.strip().split(";")
        records.append([timestamp.strip(), float(value.strip())])
    # print(records)

    df = pd.DataFrame(records,columns=["time","signal"])

    df["time"] = pd.to_datetime(df["time"],format="%d.%m.%Y %H:%M:%S,%f" )

    df=df.sort_values("time")
    df=df.set_index("time")

    return df

# since the flow event structure is different and for annnotation we need it we will load it differently

def load_events(lines:list[str])->pd.DataFrame:
    """
    takes the loaded file form the readlines() and then extract the time and event form this txt file
    Args:
    - lines (list[str]): the data got form file.readlines()
    """
    records = []

    for line in lines:
        if not(";" in line and "-" in line):
            continue # not adding the start index concept here 

        # since i dont know what the 16 stands for in below i will consider it x
        # e.g 30.05.2024 23:48:45,119-23:49:01,408; 16;Hypopnea; N1
        time_part, x, event_type, stage = line.strip().split(";")
        event_type.strip();
        x.strip();

        # 30.05.2024 23:48:45,119-23:49:01,408
        start, end = time_part.split("-")

        # i can have 2 seprate cols for data and the time but the format for the start time is same as the other files
        start_time = pd.to_datetime(start.strip(),format="%d.%m.%Y %H:%M:%S,%f")

        # end time only contains hrs:min:sec
        # extracting the dat asuing split since there is space between the date and time
        end_time = pd.to_datetime(start.split()[0]+" " +end.strip(),format="%d.%m.%Y %H:%M:%S,%f")

        records.append([start_time, end_time, event_type.strip(),stage.strip()])
    
    df = pd.DataFrame(records, columns=["start", "end", "event","stage"])

    return df

# function responsible for pdf generations and ploting
def visualize_participant(participant_folder_path):
    """
    construct pdf and save it into ~/visulisations as a form of pdf
    """
    # recurrsively findind the file path similiar to like predicate in sql eg - like "%Flow%"
    flow_list = glob.glob(participant_folder_path + "/*Flow*.txt")
    thor_files = glob.glob(participant_folder_path + "/*Thor*.txt")
    spo2_files = glob.glob(participant_folder_path + "/*SPO2*.txt")
    flow_files=[ name for name in flow_list if "event" not in name.lower()]
    event_files =[ name for name in flow_list if "event" in name.lower()]

    # select the first match and directly pass them into the load funciton
    flow_file = flow_files[0]
    thor_file = thor_files[0]
    spo2_file = spo2_files[0]
    event_file = event_files[0]

    # laoding the txt and getting df
    flow_df = load(flow_file)
    thor_df = load(thor_file)
    spo2_df = load(spo2_file)
    event_df = load(event_file)
    
    # create folder if there was none even though we have already created 
    # os.makedirs("Visualizations", exist_ok=True)
    
    folder_name = os.path.basename(participant_folder_path)
    
    output_pdf_path = f"../Visualizations/{folder_name}_visualization.pdf"
    # Assign a unique color to each event type
    unique_events = event_df["event"].unique()
    colors = ["blue", "green", "purple", "orange", "cyan", "magenta", "brown"]
    event_color_map = {}
    
    for i in range(len(unique_events)):
        event_name = unique_events[i]
        # Assign a color from our list wiht circular indexing 
        event_color_map[event_name] = colors[i % len(colors)]
    
    # 4. plot

    pdf = PdfPages(output_pdf_path)

    #Plot 1: Flow Signal
    plt.figure(figsize=(40, 5))
    plt.plot(flow_df.index, flow_df["signal"]) #this time col will come here handy
    plt.title("Nasal Airflow - 8 Hours")
    plt.xlabel("Time")
    plt.ylabel("Flow")

    seen_events = [] # ADDED: List to track legend items
    for index, row in event_df.iterrows():
        e_name = row["event"]
        e_color = event_color_map[e_name]
        
        # ADDED: Logic to only add the label to the legend once
        if e_name not in seen_events:
            plt.axvspan(row["start"], row["end"], alpha=0.3, color=e_color, label=e_name)
            seen_events.append(e_name)
        else:
            plt.axvspan(row["start"], row["end"], alpha=0.3, color=e_color)

    plt.xticks(rotation=40)
    plt.legend(loc="upper right") # ADDED: Show the legend
    
    pdf.savefig(dpi=300) #Save to PDF first or new plot will come and go only
    # plt.show()    # for testing
    plt.close()   # flush

    #Plot 2: Thoracic Signal
    plt.figure(figsize=(40, 5))
    plt.plot(thor_df.index, thor_df["signal"])
    plt.title("Thoracic Movement - 8 Hours")
    plt.xlabel("Time")
    plt.ylabel("Thoracic")

    for index, row in event_df.iterrows():
        
        plt.axvspan(row["start"], row["end"], alpha=0.3, color=event_color_map[row["event"]])

    plt.xticks(rotation=40)
    
    pdf.savefig(dpi=300)
    # plt.show()
    plt.close()

    #SPO2 Signal
    plt.figure(figsize=(40, 5))
    plt.plot(spo2_df.index, spo2_df["signal"])
    plt.title("SpO2 Level - 8 Hours")
    plt.xlabel("Time")
    plt.ylabel("SpO2 (%)")
    # here iterrows will give us iterator for a hashable index (time) and the data as series
    for index, row in event_df.iterrows():
        # CHANGED: Replaced 'orange' with the mapped color
        plt.axvspan(row["start"], row["end"], alpha=0.3, color=event_color_map[row["event"]])

    plt.xticks(rotation=40)
    
    pdf.savefig(dpi=300)
    # plt.show()
    plt.close()

    # flushig the pdf object so everthing i save 
    pdf.close()
    print(f"Visualization saved in: {output_pdf_path}")

#cli input form th user using argparse
parser = argparse.ArgumentParser()

parser.add_argument("-name", type=str, required=True)

args = parser.parse_args();

participant_file_path= args.name;

# basic check for the location  of folder since we are running in ~/scripts folder tehn we need to  amke a path

if os.path.exists(participant_file_path):
    print("Location got:", participant_file_path)

# looking one folder up (using "..") since the folder structure will be same 
elif os.path.exists(os.path.join("..", participant_file_path)):
    participant_file_path = os.path.join("..", participant_file_path)
    print("Location got (found in parent folder):", participant_file_path)


visualize_participant(participant_file_path)