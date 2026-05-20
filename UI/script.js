
document.addEventListener('DOMContentLoaded', () => {
    // 1. Tema Claro / Escuro
    const themeBtn = document.getElementById('theme-toggle');
    const body = document.body;
    
    themeBtn.addEventListener('click', () => {
        const currentTheme = body.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        body.setAttribute('data-theme', newTheme);
        
        // Atualizar icone
        const iconElement = themeBtn.querySelector('i');
        if (newTheme === 'light') {
            iconElement.setAttribute('data-feather', 'moon');
        } else {
            iconElement.setAttribute('data-feather', 'sun');
        }
        feather.replace();
    });

    // 2. Modal de Perfil
    const profileBtn = document.getElementById('profile-btn');
    const profileModal = document.getElementById('profile-modal');
    const closeModalBtn = document.getElementById('close-modal');

    profileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        profileModal.classList.toggle('show');
    });

    closeModalBtn.addEventListener('click', () => {
        profileModal.classList.remove('show');
    });

    // Fechar modal ao clicar fora
    document.addEventListener('click', (e) => {
        if (!profileModal.contains(e.target) && e.target !== profileBtn) {
            profileModal.classList.remove('show');
        }
    });

    // 3. Barra Lateral Direita (Quiz / Grafo)
    const toggleRightBtn = document.getElementById('toggle-right-sidebar');
    const closeRightBtn = document.getElementById('close-right-sidebar');
    const rightSidebar = document.getElementById('right-sidebar');

    toggleRightBtn.addEventListener('click', () => {
        rightSidebar.classList.toggle('open');
    });

    closeRightBtn.addEventListener('click', () => {
        rightSidebar.classList.remove('open');
    });

    // 4. Tabs dentro da Barra Lateral Direita
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remover active de todos
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Adicionar active ao clicado
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');
        });
    });
});
