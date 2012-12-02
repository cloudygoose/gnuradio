#!/usr/bin/env python
#
# author:htx
# combine benchmark_tx and benmark_rx from gnuradio examples
# first start listenning , at the same time, start transmitting some packets(i.e AAAAAA), 
# then the listenning callback will listen the packets itself transmitted
# 

from gnuradio import gr, blks2
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from optparse import OptionParser

import time, struct, sys


from gnuradio import digital

# from current dir
from receive_path import receive_path
from uhd_interface import uhd_receiver
from transmit_path import transmit_path
from uhd_interface import uhd_transmitter

import struct, sys

class my_top_block(gr.top_block):
    def __init__(self, callback, options):
        gr.top_block.__init__(self)
#rec
        if(options.rx_freq is not None):
            self.source = uhd_receiver(options.args,
                                       options.bandwidth,
                                       options.rx_freq, options.rx_gain,
                                       options.spec, options.antenna,
                                       options.verbose)
        elif(options.from_file is not None):
            self.source = gr.file_source(gr.sizeof_gr_complex, options.from_file)
        else:
            self.source = gr.null_source(gr.sizeof_gr_complex)

        # Set up receive path
        # do this after for any adjustments to the options that may
        # occur in the sinks (specifically the UHD sink)
        self.rxpath = receive_path(callback, options)

        self.connect(self.source, self.rxpath)
#trans
        if(options.tx_freq is not None):
            self.sink = uhd_transmitter(options.args,
                                        options.bandwidth,
                                        options.tx_freq, options.tx_gain,
                                        options.spec, options.antenna,
                                        options.verbose)
        elif(options.to_file is not None):
            self.sink = gr.file_sink(gr.sizeof_gr_complex, options.to_file)
        else:
            self.sink = gr.null_sink(gr.sizeof_gr_complex)

        # do this after for any adjustments to the options that may
        # occur in the sinks (specifically the UHD sink)
        self.txpath = transmit_path(options)

        self.connect(self.txpath, self.sink)
        


# /////////////////////////////////////////////////////////////////////////////
#                                   main
# /////////////////////////////////////////////////////////////////////////////

def main():

    global n_rcvd, n_right, rcv_buffer
        
    n_rcvd = 0
    n_right = 0
    rcv_buffer = list()
    def rx_callback(ok, payload):
        global n_rcvd, n_right, rcv_buffer
        n_rcvd += 1
        (pktno,) = struct.unpack('!H', payload[0:2])
        if ok:
            n_right += 1
            rcv_buffer.append((pktno, payload))
#            print 'pktno=', pktno, '  payload=', payload[2:]
        print "ok: %r \t pktno: %d \t n_rcvd: %d \t n_right: %d" % (ok, pktno, n_rcvd, n_right)

    def send_pkt(payload='', eof=False):
        return tb.txpath.send_pkt(payload, eof)

    parser = OptionParser(option_class=eng_option, conflict_handler="resolve")
    expert_grp = parser.add_option_group("Expert")
    parser.add_option("","--discontinuous", action="store_true", default=False,
                      help="enable discontinuous")
    parser.add_option("","--from-file", default=None,
                      help="input file of samples to demod")

    parser.add_option("","--to-file", default=None,
                      help="Output file for modulated samples")
    parser.add_option("-s", "--size", type="eng_float", default=400,
                      help="set packet size [default=%default]")
    parser.add_option("-M", "--megabytes", type="eng_float", default=1.0,
                      help="set megabytes to transmit [default=%default]")


#rcv
    receive_path.add_options(parser, expert_grp)
    uhd_receiver.add_options(parser)
    digital.ofdm_demod.add_options(parser, expert_grp)
#trans
    transmit_path.add_options(parser, expert_grp)
    digital.ofdm_mod.add_options(parser, expert_grp)
    uhd_transmitter.add_options(parser)

    (options, args) = parser.parse_args ()

    if options.from_file is None:
        if options.rx_freq is None:
            sys.stderr.write("You must specify -f FREQ or --freq FREQ\n")
            parser.print_help(sys.stderr)
            sys.exit(1)

    # build the graph
    tb = my_top_block(rx_callback, options)

    r = gr.enable_realtime_scheduling()
    if r != gr.RT_OK:
        print "Warning: failed to enable realtime scheduling"

    tb.start()                      # start flow graph
#trans
    nbytes = int(1e3 * options.megabytes)
    n = 0
    pktno = 0
    pkt_size = int(options.size)

    while n < nbytes:
        if options.from_file is None:
#            data = (pkt_size - 2) * (pktno & 0xff) 
             data = 'hellognuradio' 
        else:
            data = source_file.read(pkt_size - 2)
            if data == '':
                break;

        payload = struct.pack('!H', pktno & 0xffff) + data
        
        send_pkt(payload)
        n += len(payload)
#       sys.stderr.write('.')
        print 'transmitting pktno = ', pktno
        if options.discontinuous and pktno % 5 == 4:
            time.sleep(1)
        pktno += 1
#        print pktno, ' '
        
    send_pkt(eof=True)
    while 1:
        while len(rcv_buffer) > 0:
            (pktno, payload) = rcv_buffer.pop(0)
            print 'pktno = ', pktno, 'payload = ', payload[2:]


    tb.wait()                       # wait for it to finish

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
