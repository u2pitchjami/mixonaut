-- Nombre de pistes sans genre
SELECT COUNT(*) AS nb_sans_genre
FROM items
WHERE genre IS NULL OR genre = '' or LOWER(genre) LIKE 'none';

-- Liste des pistes concernées
SELECT artist, title, album, genre, path
FROM items
WHERE genre IS NULL OR genre = '' or LOWER(genre) LIKE 'none';

-- SELECT genre, COUNT(*) AS nb
-- FROM items
-- GROUP BY genre
-- ORDER BY nb DESC;