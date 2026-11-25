# Trigger Arc TSP

## Për projektin

Në këtë projekt jam mundu me zgjidh problemin **Trigger Arc TSP**: me gjet një rrugë që niset prej nyjës 0, kalon nëpër secilën nyjë vetëm një herë dhe kthehet prapë te nyja 0, duke pasë koston sa ma të vogël.

Problemi dallon prej TSP-së së zakonshme sepse kostoja e një harku mund të ndryshojë gjatë rrugës. Kur kaloj nëpër një hark, ai mund ta aktivizojë një *trigger* që ia ndryshon koston një harku tjetër, nëse ai hark ende nuk është përdorë. Prandaj, renditja e vizitave ka rëndësi edhe për mënyrën si ndryshojnë kostot.

Ideja ime ka qenë me ndërtu një program që i lexon të dhënat e problemit, kontrollon nëse rruga është e vlefshme, llogarit saktë koston sipas trigger-ave dhe kërkon një rrugë të lirë. Për kërkim kam dy metaheuristika: **simulated annealing**, me lëvizje 2-opt, swap dhe reinsertion, dhe **GRASP**, që ndërton cikle me zgjedhje greedy të rastësishme dhe i përmirëson me local search. E shtova edhe një zgjidhës me brute force për instanca të vogla, që me mujt me krahasu rezultatet me një kontroll të saktë.

## Si me e nisë

Nevojitet Python 3.10 ose më i ri. Nuk ka nevojë me instalu paketa shtesë. Prej PowerShell-it, në folderin e projektit, mundesh me ekzekutu shembullin:

```powershell
python main.py .\examples\small_instance.txt --seconds 30 --seed 42
```

Për me përdorë GRASP:

```powershell
python main.py .\examples\small_instance.txt --algorithm grasp --seconds 10 --seed 42 --grasp-iterations 100 --grasp-alpha 0.25
```

Te GRASP, `--grasp-iterations` cakton sa cikle ndërton dhe përmirëson, ndërsa GRASP e përdor VND-në për të shqyrtuar 2-opt, swap dhe reinsertion me kosto të trigger-ave të llogaritur saktë. `--grasp-alpha` cakton sa rastësi ka në listën e kandidatëve: `0` zgjedh vetëm kandidatët me koston më të ulët fillestare, kurse `1` lejon zgjedhje nga krejt kandidatët. `--seconds` është kufi kohe i përbashkët për kërkimin.

Programi e shfaq koston e gjetur, renditjen e nyjave dhe ID-të e harqeve të përdorura. Simulated annealing është algoritmi parazgjedhje; `--iterations` dhe `--restarts` e kontrollojnë atë. Për GRASP përdoren `--grasp-iterations` dhe `--grasp-alpha`. Të dy algoritmet e pranojnë `--seconds` dhe `--seed`.

Shto `--trace` në komandë për ta parë çdo kalim, koston e paguar dhe ndryshimet nga trigger-at:

```powershell
python main.py .\examples\small_instance.txt --seconds 5 --seed 42 --trace
```

Për me i ekzekutu testet:

```powershell
python -m unittest discover -s tests -v
```

## Formati i të dhënave

Instanca jepet si skedar tekst UTF-8. Rreshti i parë i ka numrat e nyjave, harqeve dhe marrëdhënieve. Pastaj jepen harqet me ID, nyjën prej nga nisen, nyjën ku shkojnë dhe koston fillestare. Në fund jepen marrëdhëniet trigger, të cilat tregojnë cili hark e ndryshon koston e cilit hark. ID-të dhe nyjat duhet të jenë numra të plotë; kostot mund të jenë numra të plotë ose dhjetorë.

Parser-i kontrollon që të dhënat dhe skajet e harqeve në marrëdhënie të përputhen. Nyja 0 përdoret si pikënisje dhe pikëkthim. Lejohen edhe disa harqe të ndryshme mes të njëjtave nyja.

## Organizimi i projektit

- `main.py` nis programin nga terminali.
- `parser.py` lexon dhe kontrollon skedarin e instancës.
- `graph.py` ruan nyjat, harqet dhe marrëdhëniet.
- `solution.py` kontrollon ciklin dhe llogarit koston me trigger-a.
- `metaheuristic.py` kërkon zgjidhje me simulated annealing ose GRASP.
- `brute_force.py` provon të gjitha renditjet për instanca të vogla.
- `trigger_arc_tsp.py` i bashkon funksionet kryesore për përdorim nga kodi tjetër.
- `examples/small_instance.txt` është një instancë e vogël shembull, ndërsa `tests/` përmban testet e projektit.

Kërkimi me simulated annealing është heuristik, kështu që nuk garanton se çdo herë e gjen zgjidhjen optimale. Edhe brute force bëhet shumë i ngadalshëm kur shtohen nyjat, prandaj shërben kryesisht për raste të vogla. Ky program është zgjidhës lokal; nuk e ngarkon rezultatin në portalin e garës.
