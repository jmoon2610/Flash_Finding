import ROOT
from ROOT import *
import math
import array
import sys

#Simple function returns basic info about waveform peak, amplitude, 
#point of peak, and how many times the peak value occurs as a potential check
#for pseudo-peaks. Returns relative values, no correction for actual window 
#start time
def peak_info(waveform):

    amplitude = float(max(waveform))
    amplitude_t = waveform.index(max(waveform))
    peak_count = waveform.count(amplitude)

    return amplitude, amplitude_t, peak_count


#Returns the average baseline value and baseline standard deviation, given 
#start and end points
def get_baseline_info(waveform,base_start,base_end):

    base_length = base_end-base_start+1
    baseline = waveform[base_start:(base_end+1)]
    base_avg = float(sum(baseline))/float(base_length)

    base_stdev = 0
    for x in baseline:
        base_stdev = (x - base_avg)**2
    base_stdev = math.sqrt(base_stdev/base_length)

    return base_avg,base_stdev


#Returns the total integrated charge in a waveform, then subtracts a 
#constant baseline. NOT CURRENTLY CALIBRATED
def get_charge(waveform,base_start,base_end):

    (base_avg,base_stdev) = get_baseline_info(waveform,base_start,base_end)

    charge = 0

    for x in waveform[base_end:]:
        charge = charge + x

    charge = float(charge - base_avg*(len(waveform)-base_end))

    return charge


#Searches through the list of TTL_pulse times, and then for another 
#given pulse, returns the distance to the most recent TTL pulse.
#Returns a very large value (10000) if no recent pulse is found.
#Note it finds the nearest past pulse only
def nearest_TTL(TTL_list,pulse_time):
    
    time_diff_list = []

    for x in TTL_list:

        time_diff_list.append(pulse_time -x)

    min = 100000                     #Some obvious default value of no nearest pulse found

    for x in time_diff_list:

        if (x<min and x >0):     
            min = x                  

    return min

input_file_name = sys.argv[1]
output_file_name = sys.argv[2]
input_file = ROOT.TFile(input_file_name)
output_file = ROOT.TFile(output_file_name,'RECREATE')
input_tree = input_file.Get('rawdigitwriter/RawData/OpDetWaveforms')
output_tree = ROOT.TTree('output_tree','Flasher Data Output Tree')

event_id = array.array('I',[0])
baseline_average = array.array('d',[0])
baseline_std = array.array('d',[0])
peak_amplitude = array.array('d',[0])
real_peak_time = array.array('d',[0])
frame_peak_time = array.array('I',[0])
number_of_maxima = array.array('I',[0])
total_charge = array.array('d',[0])
t_to_last_TTL = array.array('d',[0])
readout_channel = array.array('I',[0])
is_cutoff = array.array('d',[0])

output_tree.Branch('event_id',event_id,'event_id/I')
output_tree.Branch('baseline_average',baseline_average,'baseline_average/D')
output_tree.Branch('baseline_std',baseline_std,'baseline_std/D')
output_tree.Branch('peak_amplitude',peak_amplitude,'peak_amplitude/D')
output_tree.Branch('real_peak_time',real_peak_time,'real_peak_time/D')
output_tree.Branch('frame_peak_time',frame_peak_time,'frame_peak_time/I')
output_tree.Branch('number_of_maxima',number_of_maxima,'number_of_maxima/I')
output_tree.Branch('total_charge',total_charge,'total_charge/D')
output_tree.Branch('t_to_last_TTL',t_to_last_TTL,'t_to_last_TTL/D')
output_tree.Branch('readout_channel',readout_channel,'readout_channel/I')
output_tree.Branch('is_cutoff',is_cutoff,'is_cutoff/D')

window_start_times = []

#This first loop simply finds TTL pulses, i.e. those from readoudch (mod 37) =0
#then fills a list with the real pulse times

#COULD BE MORE EFFICIENT,SEVERAL REDUNDANT CALCULATIONS.  HAVEN'T BOTHERED TO FIX YET. 
for entry in input_tree:     

    waveform = []
#    if ((entry.readoutch) % 37 == 0 and entry.readoutch != 0):
    if (entry.adcs.size() == 20):
       
        for x in range(entry.adcs.size()):
            waveform.append(entry.adcs[x])

        (amplitude, amplitude_t, peak_count) = peak_info(waveform)
        start_time = entry.timestamp + amplitude_t
        window_start_times.append(start_time)

print len(window_start_times)

tick = 0
for entry in input_tree: 
    if((tick % 1000) ==0):
        print tick
    tick = tick +1
    
    baseline_start = 10             #User determined beginning of signal free region
    baseline_end = 100              #User determined end of signal free region

    waveform = []

    bins = entry.adcs.size()
    for x in range(bins):
        waveform.append(entry.adcs[x])

#    if ((entry.readoutch) % 37 !=0):
    if(entry.adcs.size() == 1500):

        (amplitude,amplitude_t,peak_count) = peak_info(waveform)
        (baseline_avg,baseline_stdev) = get_baseline_info(waveform,baseline_start,baseline_end)
        charge = get_charge(waveform,baseline_start,baseline_end)       
        absolute_peak_time = entry.timestamp + amplitude_t
        time_since_TTL = nearest_TTL(window_start_times,absolute_peak_time)
        channel = entry.readoutch
        index = entry.event
        final_bin_ratio = sum(waveform[-10:])/(baseline_avg*10.0)

        event_id[0]              = index
        baseline_average[0]      = baseline_avg
        baseline_std[0]          = baseline_stdev
        peak_amplitude[0]        = amplitude
        real_peak_time[0]        = absolute_peak_time
        frame_peak_time[0]       = amplitude_t
        number_of_maxima[0]      = peak_count
        total_charge[0]          = charge
        t_to_last_TTL[0]         = time_since_TTL
        readout_channel[0]       = channel
        is_cutoff[0]             = final_bin_ratio

        index = index + 1

        output_tree.Fill()

output_file.Write()
