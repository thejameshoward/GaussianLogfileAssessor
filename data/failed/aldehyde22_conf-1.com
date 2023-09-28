%NProcShared=40
%Mem=64GB
%chk=aldehyde22_conf-1.chk
#N OPT FREQ=NORAMAN Integral(Ultrafine) wB97XD def2SVP

aldehyde22_conf-1

0  1
O           3.85540        -0.01270         0.67100
C           3.06010         0.23010        -0.23670
C           1.58480         0.10190        -0.12570
C           0.98590        -0.31990         1.06630
C          -0.39960        -0.43320         1.14840
C          -1.19820        -0.12630         0.04110
C          -2.72020        -0.24300         0.10730
F          -3.27130         0.94440        -0.14720
F          -3.14230        -1.11370        -0.81020
F          -3.15260        -0.65450         1.30090
C          -0.59550         0.29490        -1.14820
C           0.78950         0.40900        -1.23280
H           3.41620         0.56650        -1.21100
H           1.58300        -0.56230         1.93420
H          -0.84240        -0.76050         2.07760
H          -1.20090         0.53490        -2.01030
H           1.23280         0.73660        -2.16290

--Link1--
%NProcShared=40
%Mem=64GB
%chk=aldehyde22_conf-1.chk
#N Guess=Read Geom=Check Integral(Ultrafine) Density Prop=(Potential,EFG) Volume Pop=NBO7 Pop=Hirshfeld Polar wB97XD def2TZVP

aldehyde22_conf-1

0  1

--Link1--
%NProcShared=40
%Mem=64GB
%chk=aldehyde22_conf-1.chk
#N Guess=Read Geom=Check Integral(Ultrafine) Density Pop=(ChelpG,ReadRadii) NMR wB97XD def2TZVP

aldehyde22_conf-1

0  1

