# Sample run

Captured on the revive branch with the bundled CSVs and `pandas` from `requirements.txt`.

## Baseline (60 °F)

```text
$ python climate_modeler.py --temp 60
Don Edwards SF Bay NWR Climate Modeler (toy heuristic)
Temperature: 60 °F (baseline 60 °F) → base changeVal=0
Data dir: /workspace/Don-Edwards-San-Fransisco-Bay-Wildlife-Refuge-Climate-Modeler

Birds: 
======
                   Common Name    Scientific Name  Danger Level
0  Greater White-fronted Goose    Anser albifrons             6
1                   Snow Goose    Chen hyperborea             6
2                 Ross’s Goose        Chen rossii             6
3                 Canada Goose  Branta canadensis             2
4               Cackling Goose  Branta hutchinsii             6
Max Danger Level for Birds =  61
Min Danger Level for Birds =  0
Average Danger Level for Birds =  9.46
Amount of Birds =  269

Mammals: 
========
                  Common Name           Scientific Name  Danger Level
0            Virginia opossum     Didelphis virginianus            15
1  salt marsh wandering shrew  Sorex vagrans halicoetes            11
2                 Yuma myotis         Myotis yumanensis             6
3            Western red bats     Lasirurs blossevillii             6
4                  Hoary bats         Lasiurus cinereus             6
Max Danger Level for Mammals =  61
Min Danger Level for Mammals =  0
Average Danger Level for Mammals =  10.04
Amount of Mammals =  27

Amphibians/Reptiles: 
====================
                     Common Name          Scientific Name  Danger Level
0    California tiger salamander  Ambystoma californiense            26
1            Arboreal salamander         Aneides lugubris             1
2  California slender salamander  Batrachoseps attenuatus             1
3              Pacific tree frog       Pseudacris regilla             1
4           Western fence lizard  Sceloporus occidentalis             1
Max Danger Level for Amphibians/Reptiles =  51
Min Danger Level for Amphibians/Reptiles =  1
Average Danger Level for Amphibians/Reptiles =  7.25
Amount of Amphibians/Reptiles =  12

Fish: 
======
         Common Name       Scientific Name  Danger Level
0      Leopard shark  Triakis semifasciata             6
1      Soupfin shark    Galeorhinus galeus            11
2  Brown smoothhound       Mustelus henlei             6
3          Big skate       Raja binoculata            11
4      Spiny dogfish     Squalus acanthias            11
Max Danger Level for Fish =  61
Min Danger Level for Fish =  6
Average Danger Level for Fish =  12.93
Amount of Fish =  56

Species with Danger Level ≥ 100 (treated as 'extinct' in this toy model): 0
```

## Cooler scenario (45 °F) — shows the temperature heuristic moving scores

The original EcoData curve raises `changeVal` mainly when temperature falls below the 60 °F baseline; warming above baseline yields `changeVal ≈ 0` (documented quirk of the toy formula, not a physical claim).

```text
$ python climate_modeler.py --temp 45
Don Edwards SF Bay NWR Climate Modeler (toy heuristic)
Temperature: 45 °F (baseline 60 °F) → base changeVal=25
Data dir: /workspace/Don-Edwards-San-Fransisco-Bay-Wildlife-Refuge-Climate-Modeler

Birds: 
======
                   Common Name    Scientific Name  Danger Level
0  Greater White-fronted Goose    Anser albifrons            31
1                   Snow Goose    Chen hyperborea            31
2                 Ross’s Goose        Chen rossii            31
3                 Canada Goose  Branta canadensis            27
4               Cackling Goose  Branta hutchinsii            31
Max Danger Level for Birds =  86
Min Danger Level for Birds =  0
Average Danger Level for Birds =  34.28
Amount of Birds =  269

Mammals: 
========
                  Common Name           Scientific Name  Danger Level
0            Virginia opossum     Didelphis virginianus            40
1  salt marsh wandering shrew  Sorex vagrans halicoetes            36
2                 Yuma myotis         Myotis yumanensis            31
3            Western red bats     Lasirurs blossevillii            31
4                  Hoary bats         Lasiurus cinereus            31
Max Danger Level for Mammals =  86
Min Danger Level for Mammals =  0
Average Danger Level for Mammals =  34.11
Amount of Mammals =  27

Amphibians/Reptiles: 
====================
                     Common Name          Scientific Name  Danger Level
0    California tiger salamander  Ambystoma californiense            51
1            Arboreal salamander         Aneides lugubris            26
2  California slender salamander  Batrachoseps attenuatus            26
3              Pacific tree frog       Pseudacris regilla            26
4           Western fence lizard  Sceloporus occidentalis            26
Max Danger Level for Amphibians/Reptiles =  76
Min Danger Level for Amphibians/Reptiles =  26
Average Danger Level for Amphibians/Reptiles =  32.25
Amount of Amphibians/Reptiles =  12

Fish: 
======
         Common Name       Scientific Name  Danger Level
0      Leopard shark  Triakis semifasciata            31
1      Soupfin shark    Galeorhinus galeus            36
2  Brown smoothhound       Mustelus henlei            31
3          Big skate       Raja binoculata            36
4      Spiny dogfish     Squalus acanthias            36
Max Danger Level for Fish =  86
Min Danger Level for Fish =  31
Average Danger Level for Fish =  37.93
Amount of Fish =  56

Species with Danger Level ≥ 100 (treated as 'extinct' in this toy model): 0
```
