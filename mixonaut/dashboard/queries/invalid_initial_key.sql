-- Nombre de pistes avec initial_key non valide (Camelot format minuscule)
SELECT COUNT(*) AS nb_invalid_keys
FROM items
WHERE initial_key IS NULL
   OR TRIM(initial_key) = ''
   OR LOWER(initial_key) NOT IN (
       '1a','2a','3a','4a','5a','6a','7a','8a','9a','10a','11a','12a',
       '1b','2b','3b','4b','5b','6b','7b','8b','9b','10b','11b','12b'
   );

-- Liste des pistes concernées
SELECT artist, title, album, initial_key, path
FROM items
WHERE initial_key IS NULL
   OR TRIM(initial_key) = ''
   OR LOWER(initial_key) NOT IN (
       '1a','2a','3a','4a','5a','6a','7a','8a','9a','10a','11a','12a',
       '1b','2b','3b','4b','5b','6b','7b','8b','9b','10b','11b','12b'
   );

