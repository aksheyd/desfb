# Sample run

After `python refresh_data.py` (USFWS ServCat default):

```text
Don Edwards SF Bay NWR Climate Modeler (toy heuristic)
Temperature: 60 °F (baseline 60 °F) → base changeVal=0
Data dir: /workspace/Don-Edwards-San-Fransisco-Bay-Wildlife-Refuge-Climate-Modeler/data

Birds: 
======
                   Common Name         Scientific Name  Danger Level
0  Greater White-fronted Goose         Anser albifrons             1
1             California Quail  Callipepla californica             1
2                   Snow Goose         Chen hyperborea             1
3         Ring-necked Pheasant     Phasianus colchicus             6
4                 Ross's Goose             Chen rossii             1
Max Danger Level for Birds =  61
Min Danger Level for Birds =  0
Average Danger Level for Birds =  5.35
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
