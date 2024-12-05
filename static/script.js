document.addEventListener('DOMContentLoaded', function () {
  const etudiantBtn = document.getElementById('etudiant-btn');

  if (etudiantBtn) {
      etudiantBtn.addEventListener('click', function() {
          window.location.href = '/video_feed'; // Vérifier si la redirection se fait correctement.

          fetch('/start_recognition')  
              .then(response => {
                  if (!response.ok) {
                      throw new Error(`HTTP error! status: ${response.status}`); // Gestion des erreurs HTTP.
                  }
                  return response.json();
              })
              .then(data => {
                  console.log('Status:', data.status);

              })
              .catch(error => {
                  console.error('Erreur dans l\'appel à /start_recognition:', error);
              });
      });
  } else {
      console.error('Élément "etudiant-btn" non trouvé');
  }
});
