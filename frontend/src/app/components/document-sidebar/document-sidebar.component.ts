import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-document-sidebar',
  templateUrl: './document-sidebar.component.html',
  styleUrls: ['./document-sidebar.component.css'],
})
export class DocumentSidebarComponent {
  documents: any[] = [];

  selectedFile: File | null = null;

  constructor(private http: HttpClient) {}

  onFileSelected(event: any) {
    const file = event.target.files[0];

    if (file) {
      this.selectedFile = file;
      console.log('Selected file:', file.name);
    }
  }

  uploadFile() {
    if (!this.selectedFile) {
      alert('Please select a file first');
      return;
    }

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.http
      .post('http://localhost:8000/upload', formData)
      .subscribe((res: any) => {
        console.log(res);

        this.documents.push({
          name: this.selectedFile?.name,
          date: new Date().toISOString().split('T')[0],
        });

        // reset selected file after upload
        this.selectedFile = null;
      });
  }
}
