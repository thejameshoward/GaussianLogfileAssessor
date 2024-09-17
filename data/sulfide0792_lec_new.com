%NProcShared=16
%Mem=40GB
%chk=sulfide0792_lec_new.chk
#N OPT=(CalcAll,Tight) FREQ=NORAMAN Integral(Ultrafine) B3LYP EmpiricalDispersion=GD3BJ 6-31G(d,p)

sulfide0792_lec_new

0  1
 C         -3.2360728988       -2.2904226771        0.0002327774
 S         -3.7764357616       -0.5574634247       -0.0001970205
 C         -2.2732850284        0.3635805665        0.0000420787
 C         -1.0128139415       -0.2181129812        0.0001756058
 C          0.1018887132        0.6001243590        0.0002236690
 I          2.0216047581       -0.3009424254       -0.0000325770
 C         -0.0025575314        1.9769509475        0.0000794552
 C         -1.2674409481        2.5467088009        0.0000066566
 C         -2.3948667968        1.7526693080        0.0000122450
 H         -2.6627706178       -2.5029805258       -0.8975158505
 H         -4.1492170587       -2.8776783262       -0.0002262291
 H         -2.6637115772       -2.5029058959        0.8985987525
 H         -0.8892442012       -1.2884124320        0.0002253676
 H          0.8789202384        2.5981293081        0.0000544772
 H         -1.3665350492        3.6214570833        0.0000373452
 H         -3.3804933289        2.1916000977       -0.0000107519

--Link1--
%NProcShared=16
%Mem=40GB
%chk=sulfide0792_lec_new.chk
#N Guess=Read Geom=Check Integral(Ultrafine) Density Pop=NBO7 Pop=Hirshfeld Polar Prop=(Potential,EFG) Volume  M062X def2TZVP

sulfide0792_lec_new

0  1

--Link1--
%NProcShared=16
%Mem=40GB
%chk=sulfide0792_lec_new.chk
#N Guess=Read Geom=Check Integral(Ultrafine) Density NMR Pop=(ChelpG,ReadRadii)  M062X def2TZVP

sulfide0792_lec_new

0  1

I 1.98 

