#!/usr/bin/env python
#
#    This is stepconf, a graphical configuration editor for LinuxCNC
#    Copyright 2007 Jeff Epler <jepler@unpythonic.net>
#    stepconf 1.1 revamped by Chris Morley 2014
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#    This builds the HAL files from the collected data.
#
import os
import time
import shutil

class HAL:
    def __init__(self,app):
        # access to:
        self.d = app.d  # collected data
        global SIG
        SIG = app._p    # private data (signal names)
        self.a = app    # The parent, stepconf

    def write_halfile(self, base):
        inputs = self.a.build_input_set()
        outputs = self.a.build_output_set()

        filename = os.path.join(base, self.d.machinename + ".hal")
        file = open(filename, "w")
        print(_("# Generated by stepconf 1.1 at %s") % time.asctime(), file=file)
        print(_("# If you make changes to this file, they will be").encode('utf-8'), file=file)
        print(_("# overwritten when you run stepconf again").encode('utf-8'), file=file)

        print("loadrt [KINS]KINEMATICS", file=file)
        print("loadrt [EMCMOT]EMCMOT base_period_nsec=[EMCMOT]BASE_PERIOD servo_period_nsec=[EMCMOT]SERVO_PERIOD num_joints=[KINS]JOINTS", file=file)
        port3name=port2name=port2dir=port3dir=""
        if self.d.number_pports>2:
            port3name = ' '+self.d.ioaddr3
            if self.d.pp3_direction: # Input option
                port3dir =" in"
            else: 
                port3dir =" out"
        if self.d.number_pports>1:
            port2name = ' '+self.d.ioaddr2
            if self.d.pp2_direction: # Input option
                port2dir =" in"
            else: 
                port2dir =" out"
        if not self.d.sim_hardware:
            print("loadrt hal_parport cfg=\"%s out%s%s%s%s\"" % (self.d.ioaddr, port2name, port2dir, port3name, port3dir), file=file)
        else:
            name='parport.0'
            if self.d.number_pports>1:
                name='parport.0,parport.1'
            print("loadrt sim_parport names=%s"%name, file=file)
        if self.a.doublestep():
            print("setp parport.0.reset-time %d" % self.d.steptime, file=file)
        encoder = SIG.PHA in inputs
        counter = SIG.PHB not in inputs
        probe = SIG.PROBE in inputs
        limits_homes = SIG.ALL_LIMIT_HOME in inputs
        pwm = SIG.PWM in outputs
        pump = SIG.PUMP in outputs
        if self.d.axes == 0:
            print("loadrt stepgen step_type=0,0,0", file=file)
        elif self.d.axes in(1,3):
            print("loadrt stepgen step_type=0,0,0,0", file=file)
        elif self.d.axes == 2:
            print("loadrt stepgen step_type=0,0", file=file)


        if encoder:
            print("loadrt encoder num_chan=1", file=file)
        if self.d.pyvcphaltype == 1 and self.d.pyvcpconnect == 1:
            if encoder:
                print("loadrt abs count=1", file=file)
                print("loadrt scale count=1", file=file)
                print("loadrt lowpass count=1", file=file)
                if self.d.usespindleatspeed:
                    print("loadrt near", file=file)
        if pump:
            print("loadrt charge_pump", file=file)
            print("net estop-out charge-pump.enable iocontrol.0.user-enable-out", file=file)
            print("net charge-pump <= charge-pump.out", file=file)

        if limits_homes:
            print("loadrt lut5", file=file)

        if pwm:
            print("loadrt pwmgen output_type=1", file=file)


        if self.d.classicladder:
            print("loadrt classicladder_rt numPhysInputs=%d numPhysOutputs=%d numS32in=%d numS32out=%d numFloatIn=%d numFloatOut=%d" % (self.d.digitsin , self.d.digitsout , self.d.s32in, self.d.s32out, self.d.floatsin, self.d.floatsout), file=file)

        print(file=file)
        print("addf parport.0.read base-thread", file=file)
        if self.d.number_pports > 1:
            print("addf parport.1.read base-thread", file=file)
        if self.d.number_pports > 2:
            print("addf parport.2.read base-thread", file=file)
        if self.d.sim_hardware:
            print("source sim_hardware.hal", file=file)
            if encoder:
                print("addf sim-encoder.make-pulses base-thread", file=file)
        print("addf stepgen.make-pulses base-thread", file=file)
        if encoder: print("addf encoder.update-counters base-thread", file=file)
        if pump: print("addf charge-pump base-thread", file=file)
        if pwm: print("addf pwmgen.make-pulses base-thread", file=file)
        print("addf parport.0.write base-thread", file=file)
        if self.a.doublestep():
            print("addf parport.0.reset base-thread", file=file)
        if self.d.number_pports > 1:
            print("addf parport.1.write base-thread", file=file)
        if self.d.number_pports > 2:
            print("addf parport.2.write base-thread", file=file)
        print(file=file)
        print("addf stepgen.capture-position servo-thread", file=file)
        if self.d.sim_hardware:
            print("addf sim-hardware.update servo-thread", file=file)
            if encoder:
                print("addf sim-encoder.update-speed servo-thread", file=file)
        if encoder: print("addf encoder.capture-position servo-thread", file=file)
        print("addf motion-command-handler servo-thread", file=file)
        print("addf motion-controller servo-thread", file=file)
        if self.d.classicladder:
            print("addf classicladder.0.refresh servo-thread", file=file)
        print("addf stepgen.update-freq servo-thread", file=file)

        if limits_homes:
            print("addf lut5.0 servo-thread", file=file)

        if pwm: print("addf pwmgen.update servo-thread", file=file)
        if self.d.pyvcphaltype == 1 and self.d.pyvcpconnect == 1:
            if encoder:
                print("addf abs.0 servo-thread", file=file)
                print("addf scale.0 servo-thread", file=file)
                print("addf lowpass.0 servo-thread", file=file)
                if self.d.usespindleatspeed:
                    print("addf near.0 servo-thread", file=file)
        if pwm:
            x1 = self.d.spindlepwm1
            x2 = self.d.spindlepwm2
            y1 = self.d.spindlespeed1
            y2 = self.d.spindlespeed2
            scale = (y2-y1) / (x2-x1)
            offset = x1 - y1 / scale
            print(file=file)
            print("net spindle-cmd-rpm => pwmgen.0.value", file=file)
            print("net spindle-on <= motion.spindle-on => pwmgen.0.enable", file=file)
            print("net spindle-pwm <= pwmgen.0.pwm", file=file)
            print("setp pwmgen.0.pwm-freq %s" % self.d.spindlecarrier, file=file)        
            print("setp pwmgen.0.scale %s" % scale, file=file)
            print("setp pwmgen.0.offset %s" % offset, file=file)
            print("setp pwmgen.0.dither-pwm true", file=file)

        print("net spindle-cmd-rpm     <= motion.spindle-speed-out", file=file)
        print("net spindle-cmd-rpm-abs <= motion.spindle-speed-out-abs", file=file)
        print("net spindle-cmd-rps     <= motion.spindle-speed-out-rps", file=file)
        print("net spindle-cmd-rps-abs <= motion.spindle-speed-out-rps-abs", file=file)
        print("net spindle-at-speed    => motion.spindle-at-speed", file=file)
        if SIG.ON in outputs and not pwm:
            print("net spindle-on <= motion.spindle-on", file=file)
        if SIG.CW in outputs:
            print("net spindle-cw <= motion.spindle-forward", file=file)
        if SIG.CCW in outputs:
            print("net spindle-ccw <= motion.spindle-reverse", file=file)
        if SIG.BRAKE in outputs:
            print("net spindle-brake <= motion.spindle-brake", file=file)

        if SIG.MIST in outputs:
            print("net coolant-mist <= iocontrol.0.coolant-mist", file=file)

        if SIG.FLOOD in outputs:
            print("net coolant-flood <= iocontrol.0.coolant-flood", file=file)

        if encoder:
            print(file=file)
            if SIG.PHB not in inputs:
                print("setp encoder.0.position-scale %f"\
                     % self.d.spindlecpr, file=file)
                print("setp encoder.0.counter-mode 1", file=file)
            else:
                print("setp encoder.0.position-scale %f" \
                    % ( 4.0 * int(self.d.spindlecpr)), file=file)
            print("net spindle-position encoder.0.position => motion.spindle-revs", file=file)
            print("net spindle-velocity-feedback-rps encoder.0.velocity => motion.spindle-speed-in", file=file)
            print("net spindle-index-enable encoder.0.index-enable <=> motion.spindle-index-enable", file=file)
            print("net spindle-phase-a encoder.0.phase-A", file=file)
            print("net spindle-phase-b encoder.0.phase-B", file=file)
            print("net spindle-index encoder.0.phase-Z", file=file)


        if probe:
            print(file=file)
            print("net probe-in => motion.probe-input", file=file)

        for i in range(4):
            dout = "dout-%02d" % i
            if dout in outputs:
                print("net %s <= motion.digital-out-%02d" % (dout, i), file=file)

        for i in range(4):
            din = "din-%02d" % i
            if din in inputs:
                print("net %s => motion.digital-in-%02d" % (din, i), file=file)

        print(file=file)
        for o in (1,2,3,4,5,6,7,8,9,14,16,17): self.connect_output(file, o)
        if self.d.number_pports>1:
            if self.d.pp2_direction:# Input option
                pinlist = (1,14,16,17)
            else:
                pinlist = (1,2,3,4,5,6,7,8,9,14,16,17)
            print(file=file)
            for i in pinlist: self.connect_output(file, i,1)
            print(file=file)

        for i in (10,11,12,13,15): self.connect_input(file, i)
        if self.d.number_pports>1:
            if self.d.pp2_direction: # Input option
                pinlist = (2,3,4,5,6,7,8,9,10,11,12,13,15)
            else:
                pinlist = (10,11,12,13,15)
            print(file=file)
            for i in pinlist: self.connect_input(file, i,1)
            print(file=file)

        if limits_homes:
            print("setp lut5.0.function 0x10000", file=file)
            print("net all-limit-home => lut5.0.in-4", file=file)
            print("net all-limit <= lut5.0.out", file=file)
            if self.d.axes == 2:
                print("net homing-x <= joint.0.homing => lut5.0.in-0", file=file)
                print("net homing-z <= joint.1.homing => lut5.0.in-1", file=file)
            elif self.d.axes == 0:
                print("net homing-x <= joint.0.homing => lut5.0.in-0", file=file)
                print("net homing-y <= joint.1.homing => lut5.0.in-1", file=file)
                print("net homing-z <= joint.2.homing => lut5.0.in-2", file=file)
            elif self.d.axes == 1:
                print("net homing-x <= joint.0.homing => lut5.0.in-0", file=file)
                print("net homing-y <= joint.1.homing => lut5.0.in-1", file=file)
                print("net homing-z <= joint.2.homing => lut5.0.in-2", file=file)
                print("net homing-a <= joint.3.homing => lut5.0.in-3", file=file)
            elif self.d.axes == 3:
                print("net homing-x <= joint.0.homing => lut5.0.in-0", file=file)
                print("net homing-y <= joint.1.homing => lut5.0.in-1", file=file)
                print("net homing-u <= joint.6.homing => lut5.0.in-2", file=file)
                print("net homing-v <= joint.7.homing => lut5.0.in-3", file=file)

        if self.d.axes == 2:
            self.connect_joint(file, 0, 'x')
            self.connect_joint(file, 1, 'z')
        elif self.d.axes == 0:
            self.connect_joint(file, 0, 'x')
            self.connect_joint(file, 1, 'y')
            self.connect_joint(file, 2, 'z')
        elif self.d.axes == 1:
            self.connect_joint(file, 0, 'x')
            self.connect_joint(file, 1, 'y')
            self.connect_joint(file, 2, 'z')
            self.connect_joint(file, 3, 'a')
        elif self.d.axes == 3:
            self.connect_joint(file, 0, 'x')
            self.connect_joint(file, 1, 'y')
            self.connect_joint(file, 2, 'u')
            self.connect_joint(file, 3, 'v')

        print(file=file)
        print("net estop-out <= iocontrol.0.user-enable-out", file=file)
        if  self.d.classicladder and self.d.ladderhaltype == 1 and self.d.ladderconnect: # external estop program
            print(file=file) 
            print(_("# **** Setup for external estop ladder program -START ****"), file=file)
            print(file=file)
            print("net estop-out => classicladder.0.in-00", file=file)
            print("net estop-ext => classicladder.0.in-01", file=file)
            print("net estop-strobe classicladder.0.in-02 <= iocontrol.0.user-request-enable", file=file)
            print("net estop-outcl classicladder.0.out-00 => iocontrol.0.emc-enable-in", file=file)
            print(file=file)
            print(_("# **** Setup for external estop ladder program -END ****"), file=file)
        elif SIG.ESTOP_IN in inputs:
            print("net estop-ext => iocontrol.0.emc-enable-in", file=file)
        else:
            print("net estop-out => iocontrol.0.emc-enable-in", file=file)

        print(file=file)
        if self.d.manualtoolchange:
            print("loadusr -W hal_manualtoolchange", file=file)
            print("net tool-change iocontrol.0.tool-change => hal_manualtoolchange.change", file=file)
            print("net tool-changed iocontrol.0.tool-changed <= hal_manualtoolchange.changed", file=file)
            print("net tool-number iocontrol.0.tool-prep-number => hal_manualtoolchange.number", file=file)

        else:
            print("net tool-number <= iocontrol.0.tool-prep-number", file=file)
            print("net tool-change-loopback iocontrol.0.tool-change => iocontrol.0.tool-changed", file=file)
        print("net tool-prepare-loopback iocontrol.0.tool-prepare => iocontrol.0.tool-prepared", file=file)
        if self.d.classicladder:
            print(file=file)
            if self.d.modbus:
                print(_("# Load Classicladder with modbus master included (GUI must run for Modbus)"), file=file)
                print("loadusr classicladder --modmaster custom.clp", file=file)
            else:
                print(_("# Load Classicladder without GUI (can reload LADDER GUI in AXIS GUI"), file=file)
                print("loadusr classicladder --nogui custom.clp", file=file)
        if self.d.pyvcp:
            vcp = os.path.join(base, "custompanel.xml")
            if not os.path.exists(vcp):
                f1 = open(vcp, "w")

                print("<?xml version='1.0' encoding='UTF-8'?>", file=f1)

                print("<!-- ", file=f1)
                print(_("Include your PyVCP panel here.\n"), file=f1)
                print("-->", file=f1)
                print("<pyvcp>", file=f1)
                print("</pyvcp>", file=f1)

        # Same as from pncconf
        # the jump list allows multiple hal files to be loaded postgui
        # this simplifies the problem of overwritting the users custom HAL code
        # when they change pyvcp sample options
        # if the user picked existing pyvcp option and the postgui_call_list is present
        # don't overwrite it. otherwise write the file.
        calllist_filename = os.path.join(base, "postgui_call_list.hal")
        f1 = open(calllist_filename, "w")
        print(_("# These files are loaded post GUI, in the order they appear"), file=f1)
        print(_("# Generated by stepconf 1.1 at %s") % time.asctime(), file=f1)
        print(_("# If you make changes to this file, they will be").encode('utf-8'), file=f1)
        print(_("# overwritten when you run stepconf again").encode('utf-8'), file=f1)
        print(file=f1)
        if (self.d.pyvcp):
            print("source pyvcp_options.hal", file=f1)
        print("source custom_postgui.hal", file=f1)
        f1.close()

        # If the user asked for pyvcp sample panel add the HAL commands too
        pyfilename = os.path.join(base, "pyvcp_options.hal")
        f1 = open(pyfilename, "w")
        if self.d.pyvcp and self.d.pyvcphaltype == 1 and self.d.pyvcpconnect: # spindle speed/tool # display
            print(_("# These files are loaded post GUI, in the order they appear"), file=f1)
            print(_("# Generated by stepconf 1.1 at %s") % time.asctime(), file=f1)
            print(_("# If you make changes to this file, they will be").encode('utf-8'), file=f1)
            print(_("# overwritten when you run stepconf again").encode('utf-8'), file=f1)
            print(_("# **** Setup of spindle speed display using pyvcp -START ****"), file=f1)
            if encoder:
                print(_("# **** Use ACTUAL spindle velocity from spindle encoder"), file=f1)
                print(_("# **** spindle-velocity-feedback-rps bounces around so we filter it with lowpass"), file=f1)
                print(_("# **** spindle-velocity-feedback-rps is signed so we use absolute component to remove sign"), file=f1) 
                print(_("# **** ACTUAL velocity is in RPS not RPM so we scale it."), file=f1)
                print(file=f1)
                print(("setp scale.0.gain 60"), file=f1)
                print(("setp lowpass.0.gain %f")% self.d.spindlefiltergain, file=f1)
                print(("net spindle-velocity-feedback-rps               => lowpass.0.in"), file=f1)
                print(("net spindle-fb-filtered-rps      lowpass.0.out  => abs.0.in"), file=f1)
                print(("net spindle-fb-filtered-abs-rps  abs.0.out      => scale.0.in"), file=f1)
                print(("net spindle-fb-filtered-abs-rpm  scale.0.out    => pyvcp.spindle-speed"), file=f1)
                print(file=f1)
                print(_("# **** set up spindle at speed indicator ****"), file=f1)
                if self.d.usespindleatspeed:
                    print(file=f1)
                    print(("net spindle-cmd-rps-abs             =>  near.0.in1"), file=f1)
                    print(("net spindle-velocity-feedback-rps   =>  near.0.in2"), file=f1)
                    print(("net spindle-at-speed                <=  near.0.out"), file=f1)
                    print(("setp near.0.scale %f")% self.d.spindlenearscale, file=f1)
                else:
                    print(("# **** force spindle at speed indicator true because we chose no feedback ****"), file=f1)
                    print(file=f1)
                    print(("sets spindle-at-speed true"), file=f1)
                print(("net spindle-at-speed       => pyvcp.spindle-at-speed-led"), file=f1)
            else:
                print(_("# **** Use COMMANDED spindle velocity from LinuxCNC because no spindle encoder was specified"), file=f1)
                print(file=f1)
                print(("net spindle-cmd-rpm-abs    => pyvcp.spindle-speed"), file=f1)
                print(file=f1)
                print(("# **** force spindle at speed indicator true because we have no feedback ****"), file=f1)
                print(file=f1)
                print(("net spindle-at-speed => pyvcp.spindle-at-speed-led"), file=f1)
                print(("sets spindle-at-speed true"), file=f1)
            f1.close()
        else:
            print(_("# These files are loaded post GUI, in the order they appear"), file=f1)
            print(_("# Generated by stepconf 1.1 at %s") % time.asctime(), file=f1)
            print(_("# If you make changes to this file, they will be").encode('utf-8'), file=f1)
            print(_("# overwritten when you run stepconf again").encode('utf-8'), file=f1)
            print(("sets spindle-at-speed true"), file=f1)
            f1.close()

        # stepconf adds custom.hal and custom_postgui.hal file if one is not present
        if self.d.customhal or self.d.classicladder or self.d.halui:
            for i in ("custom","custom_postgui"):
                custom = os.path.join(base, i+".hal")
                if not os.path.exists(custom):
                    f1 = open(custom, "w")
                    print(_("# Include your %s HAL commands here")%i, file=f1)
                    print(_("# This file will not be overwritten when you run stepconf again").encode('utf-8'), file=f1)
                    print(file=f1)
                    f1.close()

        file.close()
        self.sim_hardware_halfile(base)
        self.d.add_md5sum(filename)

#******************
# HELPER FUNCTIONS
#******************

    def connect_joint(self, file, num, let):
        axnum = "xyzabcuvw".index(let)
        lat = self.d.latency
        print(file=file)
        print("setp stepgen.%d.position-scale [JOINT_%d]SCALE" % (num, num), file=file)
        print("setp stepgen.%d.steplen 1" % num, file=file)
        if self.a.doublestep():
            print("setp stepgen.%d.stepspace 0" % num, file=file)
        else:
            print("setp stepgen.%d.stepspace 1" % num, file=file)
        print("setp stepgen.%d.dirhold %d" % (num, self.d.dirhold + lat), file=file)
        print("setp stepgen.%d.dirsetup %d" % (num, self.d.dirsetup + lat), file=file)
        print("setp stepgen.%d.maxaccel [JOINT_%d]STEPGEN_MAXACCEL" % (num, num), file=file)
        print("net %spos-cmd joint.%d.motor-pos-cmd => stepgen.%d.position-cmd" % (let, num, num), file=file)
        print("net %spos-fb stepgen.%d.position-fb => joint.%d.motor-pos-fb" % (let, num, num), file=file)
        print("net %sstep <= stepgen.%d.step" % (let, num), file=file)
        print("net %sdir <= stepgen.%d.dir" % (let, num), file=file)
        print("net %senable joint.%d.amp-enable-out => stepgen.%d.enable" % (let, num, num), file=file)
        homesig = self.a.home_sig(let)
        if homesig:
            print("net %s => joint.%d.home-sw-in" % (homesig, num), file=file)
        min_limsig = self.min_lim_sig(let)
        if min_limsig:
            print("net %s => joint.%d.neg-lim-sw-in" % (min_limsig, num), file=file)
        max_limsig = self.max_lim_sig(let)
        if max_limsig:
            print("net %s => joint.%d.pos-lim-sw-in" % (max_limsig, num), file=file)

    def sim_hardware_halfile(self,base):
        custom = os.path.join(base, "sim_hardware.hal")
        if self.d.sim_hardware:
            f1 = open(custom, "w")
            print(_("# This file sets up simulated limits/home/spindle encoder hardware."), file=f1)
            print(_("# This is a generated file do not edit."), file=f1)
            print(file=f1)
            inputs = self.a.build_input_set()
            if SIG.PHA in inputs:
                print("loadrt sim_encoder names=sim-encoder", file=f1)
                print("setp sim-encoder.ppr %d"%int(self.d.spindlecpr), file=f1)
                print("setp sim-encoder.scale 1", file=f1)
                print(file=f1)
                print("net spindle-cmd-rps            sim-encoder.speed", file=f1)
                print("net fake-spindle-phase-a       sim-encoder.phase-A", file=f1)
                print("net fake-spindle-phase-b       sim-encoder.phase-B", file=f1)
                print("net fake-spindle-index         sim-encoder.phase-Z", file=f1)
                print(file=f1)
            print("loadrt sim_axis_hardware names=sim-hardware", file=f1)
            print(file=f1)
            print("net Xjoint-pos-fb      joint.0.pos-fb      sim-hardware.Xcurrent-pos", file=f1)
            if self.d.axes in(0, 1): # XYZ XYZA
                print("net Yjoint-pos-fb      joint.1.pos-fb      sim-hardware.Ycurrent-pos", file=f1)
                print("net Zjoint-pos-fb      joint.2.pos-fb      sim-hardware.Zcurrent-pos", file=f1)
            if self.d.axes == 2: # XZ
                print("net Zjoint-pos-fb      joint.1.pos-fb      sim-hardware.Zcurrent-pos", file=f1)
            if self.d.axes == 1: # XYZA
                print("net Ajoint-pos-fb      joint.3.pos-fb      sim-hardware.Acurrent-pos", file=f1)
            if self.d.axes == 3: # XYUV
                print("net Yjoint-pos-fb      joint.1.pos-fb      sim-hardware.Ycurrent-pos", file=f1)
                print("net Ujoint-pos-fb      joint.2.pos-fb      sim-hardware.Ucurrent-pos", file=f1)
                print("net Vjoint-pos-fb      joint.3.pos-fb      sim-hardware.Vcurrent-pos", file=f1)
            print(file=f1)
            print("setp sim-hardware.Xmaxsw-upper 1000", file=f1)
            print("setp sim-hardware.Xmaxsw-lower [JOINT_0]MAX_LIMIT", file=f1)
            print("setp sim-hardware.Xminsw-upper [JOINT_0]MIN_LIMIT", file=f1)
            print("setp sim-hardware.Xminsw-lower -1000", file=f1)
            print("setp sim-hardware.Xhomesw-pos [JOINT_0]HOME_OFFSET", file=f1)
            print(file=f1)
            if self.d.axes in(0, 1): # XYZ XYZA
                print("setp sim-hardware.Ymaxsw-upper 1000", file=f1)
                print("setp sim-hardware.Ymaxsw-lower [JOINT_1]MAX_LIMIT", file=f1)
                print("setp sim-hardware.Yminsw-upper [JOINT_1]MIN_LIMIT", file=f1)
                print("setp sim-hardware.Yminsw-lower -1000", file=f1)
                print("setp sim-hardware.Yhomesw-pos [JOINT_1]HOME_OFFSET", file=f1)
                print(file=f1)
                print("setp sim-hardware.Zmaxsw-upper 1000", file=f1)
                print("setp sim-hardware.Zmaxsw-lower [JOINT_2]MAX_LIMIT", file=f1)
                print("setp sim-hardware.Zminsw-upper [JOINT_2]MIN_LIMIT", file=f1)
                print("setp sim-hardware.Zminsw-lower -1000", file=f1)
                print("setp sim-hardware.Zhomesw-pos [JOINT_2]HOME_OFFSET", file=f1)
                print(file=f1)
            if self.d.axes == 1: #  XYZA
                print("setp sim-hardware.Amaxsw-upper 20000", file=f1)
                print("setp sim-hardware.Amaxsw-lower [JOINT_3]MAX_LIMIT", file=f1)
                print("setp sim-hardware.Aminsw-upper [JOINT_3]MIN_LIMIT", file=f1)
                print("setp sim-hardware.Aminsw-lower -20000", file=f1)
                print("setp sim-hardware.Ahomesw-pos [JOINT_3]HOME_OFFSET", file=f1)
                print(file=f1)
            if self.d.axes == 2: # XZ
                print("setp sim-hardware.Zmaxsw-upper 1000", file=f1)
                print("setp sim-hardware.Zmaxsw-lower [JOINT_1]MAX_LIMIT", file=f1)
                print("setp sim-hardware.Zminsw-upper [JOINT_1]MIN_LIMIT", file=f1)
                print("setp sim-hardware.Zminsw-lower -1000", file=f1)
                print("setp sim-hardware.Zhomesw-pos [JOINT_1]HOME_OFFSET", file=f1)
                print(file=f1)
            if self.d.axes == 3: # XYUV
                print("setp sim-hardware.Ymaxsw-upper 1000", file=f1)
                print("setp sim-hardware.Ymaxsw-lower [JOINT_1]MAX_LIMIT", file=f1)
                print("setp sim-hardware.Yminsw-upper [JOINT_1]MIN_LIMIT", file=f1)
                print("setp sim-hardware.Yminsw-lower -1000", file=f1)
                print("setp sim-hardware.Yhomesw-pos [JOINT_1]HOME_OFFSET", file=f1)
                print(file=f1)
                print("setp sim-hardware.Umaxsw-upper 1000", file=f1)
                print("setp sim-hardware.Umaxsw-lower [JOINT_2]MAX_LIMIT", file=f1)
                print("setp sim-hardware.Uminsw-upper [JOINT_2]MIN_LIMIT", file=f1)
                print("setp sim-hardware.Uminsw-lower -1000", file=f1)
                print("setp sim-hardware.Uhomesw-pos [JOINT_2]HOME_OFFSET", file=f1)
                print(file=f1)
                print("setp sim-hardware.Vmaxsw-upper 1000", file=f1)
                print("setp sim-hardware.Vmaxsw-lower [JOINT_3]MAX_LIMIT", file=f1)
                print("setp sim-hardware.Vminsw-upper [JOINT_3]MIN_LIMIT", file=f1)
                print("setp sim-hardware.Vminsw-lower -1000", file=f1)
                print("setp sim-hardware.Vhomesw-pos [JOINT_3]HOME_OFFSET", file=f1)
                print(file=f1)
            for port in range(0,self.d.number_pports):
                print(file=f1)
                if port==0 or not self.d.pp2_direction: # output option
                    pinlist = (10,11,12,13,15)
                else:
                    pinlist = (2,3,4,5,6,7,8,9,10,11,12,13,15)
                for i in pinlist:
                    self.connect_input(f1, i, port, True)
                print(file=f1)
                if port==0 or not self.d.pp2_direction: # output option
                    pinlist = (1,2,3,4,5,6,7,8,9,14,16,17)
                else:
                    pinlist = (1,14,16,17)
                for o in pinlist:
                    self.connect_output(f1, o, port, True) 
            print(file=f1)
            print("net fake-all-home          sim-hardware.homesw-all", file=f1)
            print("net fake-all-limit         sim-hardware.limitsw-all", file=f1)
            print("net fake-all-limit-home    sim-hardware.limitsw-homesw-all", file=f1)
            print("net fake-both-x            sim-hardware.Xbothsw-out", file=f1)
            print("net fake-max-x             sim-hardware.Xmaxsw-out", file=f1)
            print("net fake-min-x             sim-hardware.Xminsw-out", file=f1)
            print("net fake-both-y            sim-hardware.Ybothsw-out", file=f1)
            print("net fake-max-y             sim-hardware.Ymaxsw-out", file=f1)
            print("net fake-min-y             sim-hardware.Yminsw-out", file=f1)
            print("net fake-both-z            sim-hardware.Zbothsw-out", file=f1)
            print("net fake-max-z             sim-hardware.Zmaxsw-out", file=f1)
            print("net fake-min-z             sim-hardware.Zminsw-out", file=f1)
            print("net fake-both-a            sim-hardware.Abothsw-out", file=f1)
            print("net fake-max-a             sim-hardware.Amaxsw-out", file=f1)
            print("net fake-min-a             sim-hardware.Aminsw-out", file=f1)
            print("net fake-both-u            sim-hardware.Ubothsw-out", file=f1)
            print("net fake-max-u             sim-hardware.Umaxsw-out", file=f1)
            print("net fake-min-u             sim-hardware.Uminsw-out", file=f1)
            print("net fake-both-v            sim-hardware.Vbothsw-out", file=f1)
            print("net fake-max-v             sim-hardware.Vmaxsw-out", file=f1)
            print("net fake-min-v             sim-hardware.Vminsw-out", file=f1)

            print("net fake-home-x            sim-hardware.Xhomesw-out", file=f1)
            print("net fake-home-y            sim-hardware.Yhomesw-out", file=f1)
            print("net fake-home-z            sim-hardware.Zhomesw-out", file=f1)
            print("net fake-home-a            sim-hardware.Ahomesw-out", file=f1)
            print("net fake-home-u            sim-hardware.Uhomesw-out", file=f1)
            print("net fake-home-v            sim-hardware.Vhomesw-out", file=f1)

            print("net fake-both-home-x       sim-hardware.Xbothsw-homesw-out", file=f1)
            print("net fake-max-home-x        sim-hardware.Xmaxsw-homesw-out", file=f1)
            print("net fake-min-home-x        sim-hardware.Xminsw-homesw-out", file=f1)

            print("net fake-both-home-y       sim-hardware.Ybothsw-homesw-out", file=f1)
            print("net fake-max-home-y        sim-hardware.Ymaxsw-homesw-out", file=f1)
            print("net fake-min-home-y        sim-hardware.Yminsw-homesw-out", file=f1)

            print("net fake-both-home-z       sim-hardware.Zbothsw-homesw-out", file=f1)
            print("net fake-max-home-z        sim-hardware.Zmaxsw-homesw-out", file=f1)
            print("net fake-min-home-z        sim-hardware.Zminsw-homesw-out", file=f1)

            print("net fake-both-home-a       sim-hardware.Abothsw-homesw-out", file=f1)
            print("net fake-max-home-a        sim-hardware.Amaxsw-homesw-out", file=f1)
            print("net fake-min-home-a        sim-hardware.Aminsw-homesw-out", file=f1)

            print("net fake-both-home-u       sim-hardware.Ubothsw-homesw-out", file=f1)
            print("net fake-max-home-u        sim-hardware.Umaxsw-homesw-out", file=f1)
            print("net fake-min-home-u        sim-hardware.Uminsw-homesw-out", file=f1)

            print("net fake-both-home-v       sim-hardware.Vbothsw-homesw-out", file=f1)
            print("net fake-max-home-v        sim-hardware.Vmaxsw-homesw-out", file=f1)
            print("net fake-min-home-v        sim-hardware.Vminsw-homesw-out", file=f1)
            f1.close()
        else:
            if os.path.exists(custom):
                os.remove(custom)

    def connect_input(self, file, num,port=0,fake=False):
        ending=''
        if port == 0:
            p = self.d['pin%d' % num]
            i = self.d['pin%dinv' % num]
        else:
            p = self.d['pp2_pin%d_in' % num]
            i = self.d['pp2_pin%d_in_inv' % num]

        if p == SIG.UNUSED_INPUT: return
        if fake:
            p='fake-'+p
            ending='-fake'
            p ='{0:<20}'.format(p)
        else:
            p ='{0:<15}'.format(p)
        if i and not fake:
            print("net %s <= parport.%d.pin-%02d-in-not%s" \
                % (p, port, num,ending), file=file)
        else:
            print("net %s <= parport.%d.pin-%02d-in%s" \
                % (p, port, num,ending), file=file)

    def connect_output(self, file, num,port=0,fake=False):
        ending=''
        if port == 0:
            p = self.d['pin%d' % num]
            i = self.d['pin%dinv' % num]
        else:
            p = self.d['pp2_pin%d' % num]
            i = self.d['pp2_pin%dinv' % num]
        if p == SIG.UNUSED_OUTPUT: return
        if fake:
            signame ='fake-'+p
            ending='-fake'
            signame ='{0:<20}'.format(signame)
        else:
            signame ='{0:<15}'.format(p)
        if i: print("setp parport.%d.pin-%02d-out-invert%s 1" %(port, num, ending), file=file)
        print("net %s => parport.%d.pin-%02d-out%s" % (signame, port, num, ending), file=file)
        if self.a.doublestep() and not fake:
            if p in (SIG.XSTEP, SIG.YSTEP, SIG.ZSTEP, SIG.ASTEP, SIG.USTEP, SIG.VSTEP):
                print("setp parport.0.pin-%02d-out-reset%s 1" % (num,ending), file=file)

    def min_lim_sig(self, axis):
        inputs = self.a.build_input_set()
        thisaxisminlimits = set((SIG.ALL_LIMIT, SIG.ALL_LIMIT_HOME, "min-" + axis, "min-home-" + axis,
                               "both-" + axis, "both-home-" + axis))
        for i in inputs:
            if i in thisaxisminlimits:
                if i==SIG.ALL_LIMIT_HOME:
                    # ALL_LIMIT is reused here as filtered signal
                    return SIG.ALL_LIMIT
                else:
                    return i

    def max_lim_sig(self, axis):
        inputs = self.a.build_input_set()
        thisaxismaxlimits = set((SIG.ALL_LIMIT, SIG.ALL_LIMIT_HOME, "max-" + axis, "max-home-" + axis,
                               "both-" + axis, "both-home-" + axis))
        for i in inputs:
            if i in thisaxismaxlimits:
                if i==SIG.ALL_LIMIT_HOME:
                    # ALL_LIMIT is reused here as filtered signal
                    return SIG.ALL_LIMIT
                else:
                    return i
    # Boiler code
    def __getitem__(self, item):
        return getattr(self, item)
    def __setitem__(self, item, value):
        return setattr(self, item, value)
