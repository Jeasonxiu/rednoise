import idlsave
from testing_loading_data_inglis2 import analyse_event

event_list=idlsave.read('/Users/ainglis/physics/event_list/event_list.sav')

for i in range(2,110):
    print 'analysing event ' + str(i) +' starting at ' + event_list.event_list.lyra_start_time[0][i]
    print 'analysing LYRA Al channel'
    analyse_event(event_number=i,wavelength='l3')
    print 'analysing LYRA Zr channel'
    analyse_event(event_number=i,wavelength='l4')
    print 'analysing RHESSI 6-12 keV channel'
    analyse_event(event_number=i,wavelength='612')
    print 'analysing RHESSI 12-25 keV channel'
    analyse_event(event_number=i,wavelength='1225')
    print 'analysing RHESSI 25-50 keV channel'
    analyse_event(event_number=i,wavelength='2550')
    print 'analysing RHESSI 50-100 keV channel'
    analyse_event(event_number=i,wavelength='50100')
    

    



