# Estrazione dati Sistema Nazionale di Valutazione

## Repository per lavoro in condivisione

Programma per estrazione dati da Sistema Nazionale di Valutazione a supporto della 4a Indagine Nazionale sugli Insegnanti Italiani (**4aI**) https://4insegnanti.it/. 

Dati estratti da: https://snv.pubblica.istruzione.it/SistemaNazionaleValutazione/

# Stato del progetto [12/09/2026]

## Obiettivo

Produrre dataset strutturati in forma matriciale. 

## Base di dati

Sono stati prodotti tramite scraping 293 file `.jsonl`, uno per ogni autonomia scolastica coinvolta nella **4aI**. Ogni file contiene multipli record, uno per ogni indicatore comunicato dall'autonomia scolastica al ministero dell'istruzione. 
Ogni record ha la seguente struttura. 


| Campo            | Descrizione                                                                                                                                                                                                                                            |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `scuola`         | Codice identificativo dell'autonomia scolastica a cui si riferisce la richiesta. Tipicamente corrisponde al codice meccanografico dell'istituto di riferimento.                                                                                                                    |
| `funzione`       | Nome della funzione o tipologia di chiamata utilizzata per recuperare i dati dal sistema SNV. Serve a distinguere endpoint o modalità di caricamento differenti.                                                                                       |
| `gruppo`         | Codice del gruppo o della sezione del RAV a cui appartiene il descrittore. Ad esempio `2.0.a`.                                                                                                                                                         |
| `descrittore`    | Codice univoco del singolo descrittore richiesto all'interno del gruppo. Ad esempio `2.0.a.1`.                                                                                                                                                         |
| `endpoint`       | URL completo dell'endpoint interrogato per ottenere i dati relativi al descrittore.                                                                                                                                                                    |
| `status`         | Codice di stato HTTP restituito dal server. Per esempio `200` indica che la richiesta HTTP è stata elaborata correttamente, ma non implica necessariamente che siano presenti dati utili.                                                              |
| `content_type`   | Tipo MIME dichiarato dalla risposta HTTP, eventualmente comprensivo della codifica dei caratteri. Ad esempio `text/html;charset=UTF-8`.                                                                                                                |
| `empty`          | Indica se il corpo della risposta HTTP è vuoto. `true` significa che non è stato restituito contenuto; `false` significa che è presente almeno del contenuto nella risposta. Non indica necessariamente la presenza di dati effettivi del descrittore. |
| `data_available` | Indica se nella risposta sono effettivamente disponibili dati relativi al descrittore. Permette di distinguere una risposta formalmente non vuota da una risposta che contiene soltanto messaggi come “Dati attualmente non disponibili”.              |
| `table_count`    | Numero di tabelle individuate nel contenuto HTML restituito dall'endpoint. Un valore pari a `0` indica che non sono state trovate tabelle.                                                                                                             |
| `html`           | Contenuto HTML grezzo restituito dal server. Può includere tabelle, script JavaScript, campi nascosti, grafici o messaggi relativi alla disponibilità dei dati. **I dati non si riferiscono necessariamente all'autonomia scolastica (campo scuola) ma a singoli plessi di cui sono riportati i meccanografici**.                                                                                        |


## Struttura della repo
 
###  Cartelle di lavoro

* _input: andranno inseriti i file di dati `.jsonl` forniti in locale ai collaboratori.
* _templates: qui andranno a salvarsi i frammenti html estratti dal renderer
* _output: qui andranno a salvarsi i file dati eventualmente prodotti per verificare l'integrità dei dati estratti

### script_py

In questa directory verranno salvati gli script prodotti.

* parsers: directory di destinazione dei singoli parser. I parser vengono scritti per ogni descrittore da estrarre. È ammesso che producano file dati con strutture diverse. 

* assembler: script di gestione del parsing e del trattamento dati prodotti. 

* renderer: strumento di visualizzazione tabelle contenute nei campi html per ogni file e record, e stampare i frammenti html in file .txt (salvati in `_templates`)
