import ROOT
from ROOT import *
import math
import array
import sys

#Function takes a waveform with multiple TTL pulses, scans through looking
#for peaks, converts the frame position to a global TTL peak time in nanoseconds.
#Function assumes that all peaks are nearly the same height in its computation
def TTL_info(waveform,frame_start_time):
    
    maximum = float(max(waveform))
    
    peak_number = 0
    peak_position = []

    for bin in range(len(waveform)):

        if (waveform[bin] > waveform[bin -10] and waveform[bin] > waveform[bin+10] and waveform[bin]/maximum > 0.95):
            position = bin + waveform[(bin-10):(bin+10)].index(max(waveform[(bin-10):(bin+10)]))
            peak_position.append(position*15.625+frame_start_time)

    peak_position = list(set(peak_position))
    peak_position.sort()
    peak_number = len(peak_position)

    return peak_number,peak_position 



#Takes a waveform and tries to establish a baseline by starting at the beginning
#of the waveform and walking through different baseline sizes to see which minimizes
#the baseline RMS
def get_baseline_info(waveform):

    baseline_start = 0
    baseline_std = 100000

    for baseline_end in [500,450,400,350,300,250,200,150,125,100,75,50,25]:
    
        trial_baseline_std = 0
        baseline_mean = float(sum(waveform[baseline_start:baseline_end]))/len(waveform[baseline_start:baseline_end])

        for x in waveform[baseline_start:baseline_end]:
            trial_baseline_std  = trial_baseline_std + (x - baseline_mean)**2

        trial_baseline_std = math.sqrt(trial_baseline_std)/float(math.sqrt(len(waveform[baseline_start:baseline_end])))


        if trial_baseline_std < baseline_std:

            baseline_std = trial_baseline_std

    return baseline_mean,baseline_std
    

#Reads in a waveform, and the list of TTL pulse real times, as well as the 
#real time at which this waveform starts. It the looks at every TTL time, opens a
#window of predetermined size, and then integrates the corresponding time window
#in the waveform, subtracts a pedestal and stores each integral separately
# in an output list.
def get_fixed_window_charge(waveform,TTL_list,waveform_start_t):

    window_width = 300                   #integration window width in ns

    charge_in_window = []

    (baseline_mean,baseline_std) = get_baseline_info(waveform)

    for TTL_start in TTL_list:
        if TTL_start + window_width > waveform_start_t + len(waveform)*15.625:     #prevents a window which will get cut off
            break

        window_start = int(round((TTL_start - waveform_start_t)/15.625))
        window_end = window_start +int(round(window_width/15.625))

        
        if len(waveform[window_start:window_end]) > 0:
            
            charge = 0
            for x in waveform[window_start:window_end]:
                charge = charge + x
    
            charge = charge - (window_end-window_start)*baseline_mean

            charge_in_window.append(charge)

 
    return charge_in_window


input_file_name = sys.argv[1]
output_file_name = sys.argv[2]
input_file = ROOT.TFile(input_file_name)
output_file = ROOT.TFile(output_file_name,'RECREATE')
input_tree = input_file.Get('rawdigitwriter/RawData/OpDetWaveforms')
output_tree = ROOT.TTree('output_tree','Flasher Data Output Tree')

event_number = array.array('I',[0])
baseline_average = array.array('d',[0])
baseline_std = array.array('d',[0])
fixed_window_charge = array.array('d',[0]*23)
readout_channel = array.array('I',[0])

output_tree.Branch('event_number',event_number,'event_number/I')
output_tree.Branch('baseline_average',baseline_average,'baseline_average/D')
output_tree.Branch('baseline_std',baseline_std,'baseline_std/D')
output_tree.Branch('fixed_window_charge',fixed_window_charge,'fixed_window_charge[23]/D')
output_tree.Branch('readout_channel',readout_channel,'readout_channel/I')

event_start_times = []

for entry in input_tree:     

    waveform = []
    if (entry.readoutch == 37):

        for x in range(entry.adcs.size()):
            waveform.append(entry.adcs[x])
            
        waveform_start_time = entry.timestamp
        num_peaks,TTL_peak_times = TTL_info(waveform,waveform_start_time)

        event_start_times.append(TTL_peak_times)
    
#At this point, event_start_times is a list of lists. Each list in the list
#corresponds to the TTL start times found for an individual event

tick = 0
for entry in input_tree:
    
    if (tick % 10000 == 0):
        print tick
    tick = tick + 1

    bins = entry.adcs.size()
    if bins != 1500:
        continue

    waveform = []
    for x in range(bins):
        waveform.append(entry.adcs[x])

    if (entry.readoutch / 100 < 37):

        real_waveform_start_t = entry.timestamp
        index = entry.event 

        (baseline_avg,baseline_stdev) = get_baseline_info(waveform)       
        channel = entry.readoutch
        window_charge = get_fixed_window_charge(waveform,event_start_times[index-1],real_waveform_start_t)
        
            
        event_number[0]          = index
        baseline_average[0]      = baseline_avg
        baseline_std[0]          = baseline_stdev
        readout_channel[0]       = channel

        for x in range(len(window_charge)):
            fixed_window_charge[x]   = window_charge[x]

        
        output_tree.Fill()

output_file.Write()
