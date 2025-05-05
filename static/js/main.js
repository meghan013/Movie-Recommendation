document.addEventListener('DOMContentLoaded', function() {
    // Rating functionality
    const ratingElements = document.querySelectorAll('.rating-stars');
    
    ratingElements.forEach(element => {
        element.addEventListener('click', function(e) {
            if (e.target.classList.contains('star')) {
                const movieId = this.dataset.movieId;
                const rating = e.target.dataset.value;
                const userId = 1; // In a real app, get from session
                
                fetch('/rate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        user_id: userId,
                        movie_id: movieId,
                        rating: rating
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Rating submitted!');
                    } else {
                        alert('Error submitting rating');
                    }
                });
            }
        });
    });
});