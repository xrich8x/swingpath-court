> **This is the VALID court table** - leak-aware, with a `split` column separating
> held-out from trained-on clips. It replaces [court_scores.md](court_scores.md),
> which measured the model on its own training data. Nothing linked here until the
> 2026-08-15 doc cleanup, while the invalid table was cited six times.

```
clip                   usable detect%  kp_err  corner within% court_IoU  false%      split
------------------------------------------------------------------------------------------
am_beginner                18     0.0     -       -       0.0       -       -     held-out
am_classB                  18     0.0     -       -       0.0       -       -   TRAINED-ON
am_college                 18    88.9     6.0     6.7    72.9       -       -   TRAINED-ON
am_fr_sud                  17     0.0     -       -       0.0       -       0.0 TRAINED-ON
am_grass1                  14     0.0     -       -       0.0       -       0.0   held-out
am_indoor_hard1            10    10.0     9.6     8.6    33.3       -      62.5   held-out
am_indoor_hard2            18     0.0     -       -       0.0       -       -   TRAINED-ON
am_lk35                    18     0.0     -       -       0.0       -       -   TRAINED-ON
am_ntrp30                  18   100.0     3.9     2.7    86.6       -       -     held-out
am_ntrp40                  18    77.8     5.1     8.2    76.0       -       -   TRAINED-ON
am_ntrp45_courtlevel       18     0.0     -       -       0.0       -       -     held-out
am_ntrp45w                 17     0.0     -       -       0.0       -       0.0 TRAINED-ON
am_ntrp50                  17    11.8    10.9     9.4    33.3       -       0.0 TRAINED-ON
am_rally32short            18     0.0     -       -       0.0       -       -   TRAINED-ON
am_rec30                   18     0.0     -       -       0.0       -       -     held-out
am_usta40                  17    76.5     6.9     6.3    58.0       -       0.0 TRAINED-ON
am_usta45                  13     0.0     -       -       0.0       -       0.0 TRAINED-ON
am_usta45final              2     0.0     -       -       0.0       -       0.0 TRAINED-ON
am_usta60                  10    60.0     4.7     3.7    74.1     0.893     0.0   held-out
am_wingfield_clay          18     0.0     -       -       0.0       -       -     held-out
------------------------------------------------------------------------------------------
HELD-OUT                  124   20.2%    (25 of 124 frames, 8 clips)
trained-on                191   23.6%    (45 of 191 frames, 12 clips)
```
