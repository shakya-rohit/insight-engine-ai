import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-document-sidebar',
  templateUrl: './document-sidebar.component.html',
  styleUrls: ['./document-sidebar.component.css'],
})
export class DocumentSidebarComponent {
  documents: any[] = [];

  constructor(private http: HttpClient) {}

  onFileSelected(event: any) {
    const file = event.target.files[0];

    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    this.http
      .post('http://localhost:8000/upload', formData)
      .subscribe((res: any) => {
        console.log(res);

        this.documents.push({
          name: file.name,
          date: new Date().toISOString().split('T')[0],
        });
      });
  }
}
