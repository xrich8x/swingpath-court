> **DO NOT USE THESE NUMBERS.** This table was produced BEFORE the court train/test
> split existed, when 17 of the 20 gold clips were also in `data/court_dataset/` -
> so every figure here is the model scored on its own training data. It has no
> `split` column and it is NOT a valid "before" for any comparison.
> **The valid, leak-aware table is [court_scores_split.md](court_scores_split.md).**
> Kept only because Session H and `train_courtnet.py` cite it as the example of
> what went wrong.

```
clip                   usable detect%  kp_err  corner within% court_IoU  false%
-------------------------------------------------------------------------------
am_beginner                18    38.9   212.0   290.2     0.0     0.114     -  
am_classB                  18    38.9   274.0   258.9     0.0     0.000     -  
am_college                 18    11.1   280.9   200.6     0.0     0.054     -  
am_ntrp30                  18     0.0     -       -       0.0       -       -  
am_ntrp40                  18     0.0     -       -       0.0       -       -  
am_ntrp45_courtlevel       18    33.3   266.3   288.3     0.0     0.000     -  
am_rally32short            18    38.9   278.7   280.3     0.0     0.004     -  
am_rec30                   18    16.7   255.4   199.2     0.0     0.000     -  
am_usta45                  13     0.0     -       -       0.0       -      60.0
```
