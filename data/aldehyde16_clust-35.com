%NProcShared=40
%Mem=64GB
%chk=aldehyde16_clust-35.chk
#N OPT FREQ=NORAMAN Integral(Ultrafine) wB97XD def2SVP

aldehyde16_clust-35

0  1
C          -5.16610         6.53530         2.60040
C          -6.06120         5.53560         2.56660
C          -6.19560         4.45480         3.62300
C          -5.91670         3.04110         3.07900
C          -5.97150         1.92850         4.14450
C          -7.36810         1.70210         4.75570
C          -7.40170         0.52510         5.75020
C          -8.76000         0.32400         6.45110
C          -9.90600        -0.10210         5.50690
C         -11.22670        -0.45880         6.21990
C         -11.89530         0.73530         6.90350
O         -12.96670         1.17940         6.49590
H          -5.12830         7.27240         1.81180
H          -4.46030         6.63220         3.41250
H          -6.74960         5.47660         1.73600
H          -5.51700         4.67500         4.44890
H          -7.21340         4.51770         4.00830
H          -4.92700         3.02920         2.61960
H          -6.61790         2.81050         2.27520
H          -5.63150         0.99810         3.68720
H          -5.25480         2.14980         4.93690
H          -7.69730         2.60760         5.26620
H          -8.08270         1.52460         3.95140
H          -6.64150         0.68850         6.51560
H          -7.11650        -0.39600         5.23980
H          -8.63900        -0.43820         7.22230
H          -9.02930         1.24030         6.97800
H         -10.09420         0.68260         4.77270
H          -9.58650        -0.97160         4.93100
H         -11.05130        -1.23020         6.97010
H         -11.92330        -0.88360         5.49610
H         -11.35990         1.15130         7.75700

--Link1--
%NProcShared=40
%Mem=64GB
%chk=aldehyde16_clust-35.chk
#N Guess=Read Geom=Check Integral(Ultrafine) Density Prop=(Potential,EFG) Volume Pop=NBO7 Pop=Hirshfeld Polar wB97XD def2TZVP

aldehyde16_clust-35

0  1

--Link1--
%NProcShared=40
%Mem=64GB
%chk=aldehyde16_clust-35.chk
#N Guess=Read Geom=Check Integral(Ultrafine) Density Pop=(ChelpG,ReadRadii) NMR wB97XD def2TZVP

aldehyde16_clust-35

0  1

