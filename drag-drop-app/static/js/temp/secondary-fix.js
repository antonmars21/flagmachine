    const box = row.querySelector('.secondary-flag-box');
    box.style.pointerEvents = 'auto';
    box.addEventListener('dragover', e => { 
        e.preventDefault(); 
        e.stopPropagation(); 
        e.dataTransfer.dropEffect = 'copy'; 
        box.style.backgroundColor = '#b3e5fc'; 
        box.style.borderColor = '#0288d1';
    });
    box.addEventListener('dragleave', e => { 
        if(e.target === box) {
            box.style.backgroundColor = '#ddd';
            box.style.borderColor = '#999';
        }
    });
    box.addEventListener('drop', e => {
        e.preventDefault();
        e.stopPropagation();
        box.style.backgroundColor = '#ddd';
        box.style.borderColor = '#999';
        try {
            const d = JSON.parse(e.dataTransfer.getData('card-data'));
            const item = state.sequence.find(s => s.id === rowId);
            if (item && d && d.flag) { 
                item.secondary_flag_image = d.flag; 
                box.innerHTML = `<img src="/static/flags/${d.flag}" alt="Secondary" style="width: 40px; height: 35px; object-fit: contain;">`; 
                syncToServer(); 
            }
        } catch(err) { 
            console.error('Secondary flag drop error:', err); 
        }
    });
